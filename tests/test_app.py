import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app
from database import add_search, get_recent_searches, init_db
from weather import CityNotFoundError, WeatherServiceError


SAMPLE_FORECAST = {
    "city": "Paris",
    "location": "Paris, Île-de-France, France",
    "current": {
        "temperature": 19.8,
        "temperature_unit": "°C",
        "feels_like": 19.1,
        "humidity": 54,
        "wind_speed": 11.2,
        "wind_unit": "km/h",
        "precipitation": 0,
        "description": "Partly cloudy",
        "is_day": True,
    },
    "days": [
        {
            "date": "2026-10-09",
            "description": "Partly cloudy",
            "high": 21,
            "low": 14,
            "precipitation": 10,
        },
        {
            "date": "2026-10-10",
            "description": "Clear sky",
            "high": 22,
            "low": 13,
            "precipitation": 0,
        },
    ],
}


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = os.path.join(self.temp_dir.name, "weather.sqlite3")
        init_db(self.database)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_persists_search_timestamp_and_returns_newest_first(self):
        add_search(self.database, "London", "London, England, UK")
        add_search(self.database, "Paris", "Paris, Île-de-France, France")

        recent = get_recent_searches(self.database)

        self.assertEqual([search["city"] for search in recent], ["Paris", "London"])
        self.assertTrue(recent[0]["searched_at"])
        self.assertEqual(recent[0]["location"], "Paris, Île-de-France, France")

    def test_recent_searches_respect_limit(self):
        for city in ("Oslo", "Rome", "Tokyo"):
            add_search(self.database, city, city)

        self.assertEqual(len(get_recent_searches(self.database, limit=2)), 2)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": os.path.join(self.temp_dir.name, "weather.sqlite3"),
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("app.get_weather", return_value=SAMPLE_FORECAST)
    def test_success_displays_conditions_forecast_and_saves_search(self, get_weather):
        response = self.client.post("/", data={"city": "Paris"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Partly cloudy", response.data)
        self.assertIn(b"5-day forecast", response.data)
        self.assertIn(b"Sat", response.data)
        self.assertIn(b"Recent searches", response.data)
        self.assertEqual(get_recent_searches(self.app.config["DATABASE"])[0]["city"], "Paris")
        get_weather.assert_called_once_with("Paris", timeout=8)

    @patch("app.get_weather", side_effect=CityNotFoundError("Atlantis"))
    def test_unknown_city_shows_message_and_is_not_saved(self, _get_weather):
        response = self.client.post("/", data={"city": "Atlantis"})

        self.assertIn(b"We couldn&#39;t find", response.data)
        self.assertEqual(get_recent_searches(self.app.config["DATABASE"]), [])

    @patch("app.get_weather", side_effect=WeatherServiceError("network failure"))
    def test_upstream_error_is_user_friendly_and_not_saved(self, _get_weather):
        response = self.client.post("/", data={"city": "Paris"})

        self.assertIn(b"Weather data is temporarily unavailable", response.data)
        self.assertEqual(get_recent_searches(self.app.config["DATABASE"]), [])

    def test_empty_city_is_validated_without_calling_service(self):
        with patch("app.get_weather") as get_weather:
            response = self.client.post("/", data={"city": "  "})

        self.assertIn(b"Enter a city to see its weather", response.data)
        get_weather.assert_not_called()


if __name__ == "__main__":
    unittest.main()
