import os
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request

from database import add_search, get_recent_searches, init_db
from weather import CityNotFoundError, WeatherServiceError, get_weather


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=os.environ.get(
            "WEATHER_DATABASE", str(Path(app.instance_path) / "weather.sqlite3")
        ),
        RECENT_SEARCH_LIMIT=5,
        WEATHER_TIMEOUT=8,
    )
    if test_config:
        app.config.update(test_config)

    app.jinja_env.filters["date_label"] = lambda value: datetime.strptime(value, "%Y-%m-%d").strftime("%a")

    def weather_symbol(_value, description):
        description = description.lower()
        if "thunderstorm" in description:
            return "⛈"
        if "snow" in description:
            return "❄"
        if "rain" in description or "drizzle" in description:
            return "☂"
        if "cloud" in description or "overcast" in description:
            return "☁"
        return "☀"

    app.jinja_env.filters["weather_symbol"] = weather_symbol

    @app.route("/health", methods=["GET"])
    def health():
        return {"status": "healthy"}, 200

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    init_db(app.config["DATABASE"])

    @app.route("/", methods=["GET", "POST"])
    def index():
        error = None
        forecast = None
        city = ""

        if request.method == "POST":
            city = request.form.get("city", "").strip()
            if not city:
                error = "Enter a city to see its weather."
            else:
                try:
                    forecast = get_weather(city, timeout=app.config["WEATHER_TIMEOUT"])
                    add_search(
                        app.config["DATABASE"],
                        forecast["city"],
                        forecast["location"],
                    )
                except CityNotFoundError:
                    error = f"We couldn't find “{city}”. Check the spelling and try again."
                except WeatherServiceError as exc:
                    app.logger.warning("Weather lookup failed: %s", exc)
                    error = "Weather data is temporarily unavailable. Please try again."

        recent_searches = get_recent_searches(
            app.config["DATABASE"], app.config["RECENT_SEARCH_LIMIT"]
        )
        return render_template(
            "index.html",
            forecast=forecast,
            city=city,
            error=error,
            recent_searches=recent_searches,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
