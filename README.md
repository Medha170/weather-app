# Daybreak Weather

A small Flask weather app that looks up a city with Open-Meteo, shows current conditions and a five-day forecast, and keeps a short list of successful searches. Open-Meteo is free to use and does not require an API key.

## Setup

Requires Python 3.9 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. Search for a city by name. The app picks the first geocoding result returned by Open-Meteo. Weather lookups need an internet connection.

## Configuration

- `WEATHER_DATABASE`: SQLite database file path. Defaults to `instance/weather.sqlite3` in this project.
- The Open-Meteo request timeout defaults to 8 seconds. It can be adjusted in `create_app` configuration with `WEATHER_TIMEOUT`.
- Set `FLASK_DEBUG=1` to enable Flask's development debugger. Do not enable it on a public server.

## Search history and data

The SQLite database is initialized automatically on app startup. Each successful lookup adds the resolved city and location with a UTC timestamp. The home page shows up to five most recent successful searches; failed lookups are not stored. Search history is local to the configured database file and is not sent to Open-Meteo.

## Tests

```sh
python -m unittest discover -s tests -v
```

The tests use a temporary SQLite database and mock the weather API, so they do not need network access.
