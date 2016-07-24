Upstream's not accepting PRs, let's fork!

Things you'll need beforehand:
- A pokemon.com account (I'd suggest [making an account][3] separate from the one
  you play on since this probably violates the TOS).
- A google maps api key.  You can create one [here] [1].
- A lat / lng of your location. You can use the [google geocoder] [2].

Rough usage:

- Set up `config.json`
    Usually:
    - `cp config.example.json config.json`
    - `chmod 600 config.json`
    - `$EDITOR config.json`
- `make venv`
- `. venv/bin/activate`
- `pgctl-2015 start`


[1]: https://console.developers.google.com/flows/enableapi?apiid=maps_backend,geocoding_backend,directions_backend,distance_matrix_backend,elevation_backend,places_backend&keyType=CLIENT_SIDE&reusekey=true
[2]: https://developers.google.com/maps/documentation/utils/geocoder/
[3]: https://club.pokemon.com/us/pokemon-trainer-club/sign-up/
