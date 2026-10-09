import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Freezing drizzle",
    57: "Heavy freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light showers",
    81: "Rain showers",
    82: "Heavy showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


class CityNotFoundError(Exception):
    pass


class WeatherServiceError(Exception):
    pass


def _request_json(url, params, timeout):
    request_url = f"{url}?{urlencode(params)}"
    try:
        with urlopen(request_url, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WeatherServiceError("Open-Meteo request failed") from exc
    if not isinstance(data, dict):
        raise WeatherServiceError("Open-Meteo returned an invalid response")
    return data


def _description(code):
    return WEATHER_DESCRIPTIONS.get(code, "Weather conditions")


def get_weather(city, timeout=8):
    geocoding = _request_json(
        GEOCODING_URL,
        {"name": city, "count": 1, "language": "en", "format": "json"},
        timeout,
    )
    if geocoding.get("error"):
        raise WeatherServiceError(geocoding.get("reason", "Geocoding request failed"))
    locations = geocoding.get("results")
    if not locations:
        raise CityNotFoundError(city)

    try:
        place = locations[0]
        forecast_data = _request_json(
            FORECAST_URL,
            {
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "is_day,precipitation,weather_code,wind_speed_10m"
                ),
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_probability_max"
                ),
                "forecast_days": 5,
                "timezone": "auto",
            },
            timeout,
        )
        if forecast_data.get("error"):
            raise WeatherServiceError(forecast_data.get("reason", "Forecast request failed"))

        current = forecast_data["current"]
        units = forecast_data.get("current_units", {})
        daily = forecast_data["daily"]
        location_parts = [place.get("name"), place.get("admin1"), place.get("country")]
        location = ", ".join(dict.fromkeys(part for part in location_parts if part))
        days = [
            {
                "date": date,
                "description": _description(code),
                "high": high,
                "low": low,
                "precipitation": probability,
            }
            for date, code, high, low, probability in zip(
                daily["time"],
                daily["weather_code"],
                daily["temperature_2m_max"],
                daily["temperature_2m_min"],
                daily["precipitation_probability_max"],
            )
        ]
        return {
            "city": place["name"],
            "location": location,
            "current": {
                "temperature": current["temperature_2m"],
                "temperature_unit": units.get("temperature_2m", "°C"),
                "feels_like": current["apparent_temperature"],
                "humidity": current["relative_humidity_2m"],
                "wind_speed": current["wind_speed_10m"],
                "wind_unit": units.get("wind_speed_10m", "km/h"),
                "precipitation": current["precipitation"],
                "description": _description(current["weather_code"]),
                "is_day": bool(current["is_day"]),
            },
            "days": days,
        }
    except WeatherServiceError:
        raise
    except (AttributeError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise WeatherServiceError("Open-Meteo returned incomplete weather data") from exc
