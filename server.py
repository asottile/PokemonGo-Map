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
    ignore = {name.lower() for name in config['ignore']}

with open('pokemon.en.json') as pokemon_names_file:
    pokemon_names = {
        int(k): v for k, v in json.load(pokemon_names_file).items()
    }


def time_left(ms):
    s = ms / 1000
    (m, s) = divmod(s, 60)
    (h, m) = divmod(m, 60)
    return (h, m, s)


app = flask.Flask(__name__, template_folder='templates')


@app.route('/data')
def data():
    """ Gets all the PokeMarkers via REST """
    return flask.jsonify(get_pokemarkers())


@app.route('/config')
def config():
    return flask.jsonify({
        'lat': origin_lat,
        'lng': origin_lng,
        'zoom': zoom,
        'identifier': "fullmap"
    })


@app.route('/')
def fullmap():
    if 'refresh' in flask.request.args:
        auto_refresh_interval = int(flask.request.args['refresh'])
    else:
        auto_refresh_interval = auto_refresh
    return flask.render_template(
        'map.html',
        key=GOOGLEMAPS_KEY,
        auto_refresh=auto_refresh_interval,
        # Mobile browsers cache forever, let's at least give them a hint about
        # the timestamp
        timestamp=os.stat('static/css/main.css').st_mtime,
    )


ORIGIN_ICON = {
    'icon': '//maps.google.com/mapfiles/ms/icons/red-dot.png',
    'lat': origin_lat,
    'lng': origin_lng,
    'infobox': "Start position",
    'type': 'custom',
    'key': 'start-position',
    'disappear_time': -1
}


LABEL_TEMPLATE = (
    '<div><b>{pokemon.name}</b></div>'
    '<div>Disappears at - {pokemon.expires_at_formatted} '
    '<span class="label-countdown" disappears-at="{pokemon.expires_at}">'
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
            'key': self.spawn_id,
            'pokemon': self.number,
            'disappear_time': self.expires_at,
            'icon': 'static/icons/{}.png'.format(self.number),
            'lat': self.lat,
            'lng': self.lng,
            'infobox': LABEL_TEMPLATE.format(pokemon=self),
        }


def get_pokemarkers():
    current_time_ms = time.time() * 1000
    with connect_db() as db:
        data = DATA.select_non_expired(db, current_time_ms)
        lure_data = LURE_DATA.select_non_expired(db, current_time_ms)
        all_data = [Pokemon(*row) for row in data + lure_data]

    return [ORIGIN_ICON] + [
        pokemon.to_marker() for pokemon in all_data
        if pokemon.name.lower() not in ignore
    ]


if __name__ == '__main__':
    app.run(debug=True, use_evalex=False, processes=5, host=host, port=port)
