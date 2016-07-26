# -*- coding: utf-8 -*-
import collections
import sqlite3
import math
import re
import struct
import json
import time
from datetime import datetime

import requests
from google.protobuf.internal import encoder
from google.protobuf.message import DecodeError
from s2sphere import CellId
from s2sphere import LatLng
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.adapters import ConnectionError
from requests.models import InvalidURL

import pokemon_pb2


requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

API_URL = 'https://pgorelease.nianticlabs.com/plfe/rpc'
LOGIN_URL = \
    'https://sso.pokemon.com/sso/login?service=https://sso.pokemon.com/sso/oauth2.0/callbackAuthorize'
LOGIN_OAUTH = 'https://sso.pokemon.com/sso/oauth2.0/accessToken'

PTC_CLIENT_SECRET = 'w8ScCUXJQc6kXKw8FiOhd8Fixzht18Dq3PEVkUCP5ZPxtgyWsbTvWHFLm2wNY0JR'

SESSION = requests.session()
SESSION.headers.update({'User-Agent': 'Niantic App'})
SESSION.verify = False


class Location(collections.namedtuple('Location', ('lat', 'lng'))):
    __slots__ = ()

    @property
    def lat_i(self):
        return f2i(self.lat)

    @property
    def lng_i(self):
        return f2i(self.lng)

    @property
    def lat_lng(self):
        return LatLng.from_degrees(*self)


with open('config.json') as config:
    config = json.load(config)
    global_password = config['password']
    global_username = config['username']
    origin = Location(config['latitude'], config['longitude'])
    steplimit = config['steplimit']


def encode(cellid):
    output = []
    encoder._VarintEncoder()(output.append, cellid)
    return ''.join(output)


def get_neighbors(loc):
    origin = CellId.from_lat_lng(loc.lat_lng).parent(15)
    walk = [origin.id()]

    # 10 before and 10 after
    next = origin.next()
    prev = origin.prev()
    for i in range(10):
        walk.append(prev.id())
        walk.append(next.id())
        next = next.next()
        prev = prev.prev()
    return walk


def f2i(float):
    return struct.unpack('<Q', struct.pack('<d', float))[0]


def retrying_api_req(*args, **kwargs):
    while True:
        try:
            response = api_req(*args, **kwargs)
            if response:
                return response
            print('retrying_api_req: api_req returned None, retrying')
        except (InvalidURL, ConnectionError, DecodeError) as e:
            print('retrying_api_req: request error ({!r}), retrying'.format(e))
        time.sleep(1)


def api_req(api_endpoint, access_token, *args, **kwargs):
    loc = kwargs.pop('loc')
    p_req = pokemon_pb2.RequestEnvelop()
    p_req.rpc_id = 1469378659230941192

    p_req.unknown1 = 2

    p_req.latitude, p_req.longitude, p_req.altitude = loc.lat_i, loc.lng_i, 0

    p_req.unknown12 = 989

    if 'useauth' not in kwargs or not kwargs['useauth']:
        p_req.auth.provider = 'ptc'
        p_req.auth.token.contents = access_token
        p_req.auth.token.unknown13 = 14
    else:
        p_req.unknown11.unknown71 = kwargs['useauth'].unknown71
        p_req.unknown11.unknown72 = kwargs['useauth'].unknown72
        p_req.unknown11.unknown73 = kwargs['useauth'].unknown73

    for arg in args:
        p_req.MergeFrom(arg)

    protobuf = p_req.SerializeToString()

    r = SESSION.post(api_endpoint, data=protobuf, verify=False)

    p_ret = pokemon_pb2.ResponseEnvelop()
    p_ret.ParseFromString(r.content)

    time.sleep(0.51)
    return p_ret


def get_api_endpoint(access_token, loc):
    profile_response = None
    while not profile_response:
        profile_response = retrying_get_profile(access_token, API_URL, None, loc)
        if not hasattr(profile_response, 'api_url'):
            print('retrying_get_profile: get_profile returned no api_url, retrying')
            profile_response = None
            continue
        if not len(profile_response.api_url):
            print('get_api_endpoint: retrying_get_profile returned no-len api_url, retrying')
            profile_response = None

    return 'https://%s/rpc' % profile_response.api_url


def retrying_get_profile(access_token, api, useauth, loc):
    profile_response = None
    while not profile_response:
        profile_response = get_profile(access_token, api, useauth, loc=loc)
        if not hasattr(profile_response, 'payload'):
            print('retrying_get_profile: get_profile returned no payload, retrying')
            profile_response = None
            continue
        if not profile_response.payload:
            print('retrying_get_profile: get_profile returned no-len payload, retrying')
            profile_response = None

    return profile_response


def get_profile(access_token, api, useauth, *reqq, **kwargs):
    loc = kwargs.pop('loc')
    assert not kwargs, kwargs
    req = pokemon_pb2.RequestEnvelop()
    req1 = req.requests.add()
    req1.type = 2
    if len(reqq) >= 1:
        req1.MergeFrom(reqq[0])

    req2 = req.requests.add()
    req2.type = 126
    if len(reqq) >= 2:
        req2.MergeFrom(reqq[1])

    req3 = req.requests.add()
    req3.type = 4
    if len(reqq) >= 3:
        req3.MergeFrom(reqq[2])

    req4 = req.requests.add()
    req4.type = 129
    if len(reqq) >= 4:
        req4.MergeFrom(reqq[3])

    req5 = req.requests.add()
    req5.type = 5
    if len(reqq) >= 5:
        req5.MergeFrom(reqq[4])
    return retrying_api_req(api, access_token, req, loc=loc, useauth=useauth)


def login_ptc(username, password):
    print '[!] PTC login for: {}'.format(username)
    head = {'User-Agent': 'Niantic App'}
    r = SESSION.get(LOGIN_URL, headers=head)
    if r is None:
        raise AssertionError('No login')

    try:
        jdata = json.loads(r.content)
    except ValueError:
        print('login_ptc: could not decode JSON from {}'.format(r.content))
        return None

    # Maximum password length is 15 (sign in page enforces this limit, API does not)

    if len(password) > 15:
        print '[!] Trimming password to 15 characters'
        password = password[:15]

    data = {
        'lt': jdata['lt'],
        'execution': jdata['execution'],
        '_eventId': 'submit',
        'username': username,
        'password': password,
    }
    r1 = SESSION.post(LOGIN_URL, data=data, headers=head)

    ticket = None
    try:
        ticket = re.sub('.*ticket=', '', r1.history[0].headers['Location'])
    except Exception:
        return None

    data1 = {
        'client_id': 'mobile-app_pokemon-go',
        'redirect_uri': 'https://www.nianticlabs.com/pokemongo/error',
        'client_secret': PTC_CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'code': ticket,
    }
    r2 = SESSION.post(LOGIN_OAUTH, data=data1)
    access_token = re.sub('&expires.*', '', r2.content)
    access_token = re.sub('.*access_token=', '', access_token)

    return access_token


def get_heartbeat(api_endpoint, access_token, response, loc):
    m4 = pokemon_pb2.RequestEnvelop.Requests()
    m = pokemon_pb2.RequestEnvelop.MessageSingleInt()
    m.f1 = int(time.time() * 1000)
    m4.message = m.SerializeToString()
    m5 = pokemon_pb2.RequestEnvelop.Requests()
    m = pokemon_pb2.RequestEnvelop.MessageSingleString()
    m.bytes = '05daf51635c82611d1aac95c0b051d3ec088a930'
    m5.message = m.SerializeToString()
    walk = sorted(get_neighbors(loc))
    m1 = pokemon_pb2.RequestEnvelop.Requests()
    m1.type = 106
    m = pokemon_pb2.RequestEnvelop.MessageQuad()
    m.f1 = ''.join(map(encode, walk))
    m.f2 = \
        "\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000"
    m.lat, m.long = loc.lat_i, loc.lng_i
    m1.message = m.SerializeToString()
    response = get_profile(
        access_token,
        api_endpoint,
        response.unknown7,
        m1,
        pokemon_pb2.RequestEnvelop.Requests(),
        m4,
        pokemon_pb2.RequestEnvelop.Requests(),
        m5,
        loc=loc,
    )

    try:
        payload = response.payload[0]
    except (AttributeError, IndexError):
        return

    heartbeat = pokemon_pb2.ResponseEnvelop.HeartbeatPayload()
    heartbeat.ParseFromString(payload)
    return heartbeat


def get_token(username, password):
    return login_ptc(username, password)


def login(origin):
    access_token = get_token(global_username, global_password)
    if access_token is None:
        raise Exception('[-] Wrong username/password')

    print '[+] RPC Session Token: {} ...'.format(access_token[:25])

    api_endpoint = get_api_endpoint(access_token, origin)
    if api_endpoint is None:
        raise Exception('[-] RPC server offline')

    print '[+] Received API endpoint: {}'.format(api_endpoint)

    profile_response = retrying_get_profile(access_token, api_endpoint, None, origin)
    if profile_response is None or not profile_response.payload:
        raise Exception('Could not get profile')

    print '[+] Login successful'

    payload = profile_response.payload[0]
    profile = pokemon_pb2.ResponseEnvelop.ProfilePayload()
    profile.ParseFromString(payload)
    print '[+] Username: {}'.format(profile.profile.username)

    creation_time = \
        datetime.fromtimestamp(int(profile.profile.creation_time) / 1000)
    print '[+] You started playing Pokemon Go on: {}'.format(
        creation_time.strftime('%Y-%m-%d %H:%M:%S'))

    for curr in profile.profile.currency:
        print '[+] {}: {}'.format(curr.type, curr.amount)

    return api_endpoint, access_token, profile_response


def create_tables(db):
    results = db.execute(
        'SELECT name '
        'FROM sqlite_master '
        'WHERE type="table" and name="data"'
    ).fetchall()
    if not results:
        db.execute(
            'CREATE TABLE data (\n'
            '    spawn_id CHAR(12) NOT NULL,\n'
            '    pokemon INT NOT NULL,\n'
            '    lat FLOAT NOT NULL,\n'
            '    lng FLOAT NOT NULL,\n'
            '    expires_at_ms INT NOT NULL,\n'
            '    PRIMARY KEY (spawn_id, expires_at_ms)\n'
            ')'
        )


def insert_data(db, data):
    db.executemany(
        'INSERT OR REPLACE INTO data\n'
        '(spawn_id, pokemon, lat, lng, expires_at_ms)\n'
        'VALUES (?, ?, ?, ?, ?)',
        data,
    )


def generate_location_steps2(num_steps):
    x, y = 0, 0
    yield x, y
    for n in range(1, num_steps):
        n += 1
        for i in range(1, n):
            x += 1
            yield x, y
        for i in range(1, n - 1):
            y += 1
            yield x, y
        for i in range(1, n):
            x -= 1
            y += 1
            yield x, y
        for i in range(1, n):
            x -= 1
            yield x, y
        for i in range(1, n):
            y -= 1
            yield x, y
        for i in range(1, n):
            x += 1
            y -= 1
            yield x, y
    for i in range(1, num_steps):
        x += 1
        yield x, y


# the height of the unit equilateral triangle
UNIT_TRIANGLE_HEIGHT = (3 ** 0.5) / 2.0


def generate_location_steps3(num_steps):
    for x, y in generate_location_steps2(num_steps):
        yield x + (y / 2.0), y * UNIT_TRIANGLE_HEIGHT


def generate_location_steps4(loc, num_steps):
    meters_delta = 150
    # Conversion of radius from meters to deg
    lat_delta = meters_delta / M_PER_DEG
    lng_delta = meters_delta / M_PER_DEG / math.cos(loc.lat * 0.0174533)
    for x, y in generate_location_steps3(num_steps):
        yield Location(x * lat_delta + loc.lat, y * lng_delta + loc.lng)


M_PER_DEG = 111111.


def main():
    api_endpoint, access_token, profile_response = login(origin)

    with sqlite3.connect('database.db') as db:
        create_tables(db)

    while True:
        for loc in generate_location_steps4(origin, steplimit):
            hh = get_heartbeat(api_endpoint, access_token, profile_response, loc)
            data = []
            for cell in hh.cells:
                for poke in cell.WildPokemon:
                    disappear_ms = cell.AsOfTimeMs + poke.TimeTillHiddenMs
                    data.append((
                        poke.SpawnPointId,
                        poke.pokemon.PokemonId,
                        poke.Latitude,
                        poke.Longitude,
                        disappear_ms,
                    ))
            if data:
                print('Upserting {} pokemon'.format(len(data)))
                with sqlite3.connect('database.db') as db:
                    insert_data(db, data)


if __name__ == '__main__':
    exit(main())
