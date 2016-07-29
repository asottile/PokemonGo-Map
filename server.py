import collections
import json
import os
import time
from datetime import datetime

import flask

from _db_logic import connect_db
from _db_logic import DATA
from _db_logic import LURE_DATA


with open('config.json') as config:
    config = json.load(config)
    origin_lat = config['latitude']
    origin_lng = config['longitude']
    GOOGLEMAPS_KEY = config['gmaps_key']
    host = config['host']
    port = config['port']
    auto_refresh = config['auto_refresh']
    zoom = config['zoom']

with open('pokemon.en.json') as pokemon_names_file:
    pokemon_names = json.load(pokemon_names_file)


def time_left(ms):
    s = ms / 1000
    (m, s) = divmod(s, 60)
    (h, m) = divmod(m, 60)
    return (h, m, s)


app = flask.Flask(__name__, template_folder='templates')


@app.route('/data')
def data():
    if 'ignore' in flask.request.args:
        ignore = {int(x) for x in flask.request.args['ignore'].split(',')}
    else:
        ignore = set()
    return flask.jsonify(get_pokemarkers(ignore))


@app.route('/')
def fullmap():
    if 'refresh' in flask.request.args:
        auto_refresh_interval = int(flask.request.args['refresh'])
    else:
        auto_refresh_interval = auto_refresh
    return flask.render_template(
        'map.html',
        key=GOOGLEMAPS_KEY,
        js_globals={
            'auto_refresh': auto_refresh_interval * 1000,
            'origin_lat': origin_lat,
            'origin_lng': origin_lng,
            'pokemon': pokemon_names,
            'zoom': zoom,
        },
        # Mobile browsers cache forever, let's at least give them a hint about
        # the timestamp
        css_timestamp=os.stat('static/css/main.css').st_mtime,
        js_timestamp=os.stat('static/js/main.js').st_mtime,
    )


LABEL_TEMPLATE = (
    '<div><b>{pokemon.name}</b></div>'
    '<div>Disappears at - {pokemon.expires_at_formatted} '
    '<span class="label-countdown" disappears-at="{pokemon.expires_at_ms}">'
    '</span></div>'
)


class Pokemon(collections.namedtuple(
        'Pokemon', ('spawn_id', 'number', 'lat', 'lng', 'expires_at_ms'),
)):
    @property
    def name(self):
        return pokemon_names[self.number]

    @property
    def expires_at(self):
        return self.expires_at_ms / 1000

    @property
    def expires_at_formatted(self):
        return datetime.fromtimestamp(self.expires_at).strftime('%H:%M:%S')

    def to_marker(self):
        return {
            'type': 'pokemon',
            'key': '{}@{}'.format(self.spawn_id, self.expires_at_ms),
            'pokemon': self.number,
            'disappear_time': self.expires_at_ms,
            'icon': 'static/icons/{}.png'.format(self.number),
            'lat': self.lat,
            'lng': self.lng,
            'infobox': LABEL_TEMPLATE.format(pokemon=self),
        }


def get_pokemarkers(ignore):
    current_time_ms = time.time() * 1000
    with connect_db() as db:
        data = DATA.select_non_expired(db, current_time_ms)
        lure_data = LURE_DATA.select_non_expired(db, current_time_ms)
        all_data = [Pokemon(*row) for row in data + lure_data]

    return [
        pokemon.to_marker() for pokemon in all_data
        if pokemon.number not in ignore
    ]


if __name__ == '__main__':
    app.run(debug=True, use_evalex=False, processes=5, host=host, port=port)
