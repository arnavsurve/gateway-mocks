import os
from functools import wraps
from typing import Any, Dict, Optional

import requests
from apiflask import APIFlask
from flask import jsonify, request

app = APIFlask(__name__)


class WeatherGovClient:
    """Client for interacting with the api.weather.gov API."""

    BASE_URL = "https://api.weather.gov/"

    def __init__(self, user_agent: str = "WeatherAPIServer/1.0"):
        """Initialize the Weather.gov API client."""
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": user_agent, "Accept": "application/geo+json"}
        )

    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to the API."""
        url = self.BASE_URL + endpoint
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_point_metadata(self, lat: float, lon: float) -> Dict:
        """Get metadata for a specific lat/lon point."""
        point = f"{lat},{lon}"
        data = self._request(f"points/{point}")
        return {
            "grid_id": data["properties"]["gridId"],
            "grid_x": data["properties"]["gridX"],
            "grid_y": data["properties"]["gridY"],
            "forecast_url": data["properties"]["forecast"],
            "hourly_forecast_url": data["properties"]["forecastHourly"],
        }

    def get_forecast(
        self, lat: float, lon: float, hourly: bool = False
    ) -> Dict[str, Any]:
        """Get a weather forecast for a location."""
        point_data = self.get_point_metadata(lat, lon)

        if hourly:
            forecast_url = point_data["hourly_forecast_url"].replace(self.BASE_URL, "")
        else:
            forecast_url = point_data["forecast_url"].replace(self.BASE_URL, "")

        data = self._request(forecast_url)

        # Simplify the data structure for easier use
        forecast = {"updated": data["properties"]["updateTime"], "periods": []}

        for period in data["properties"]["periods"]:
            forecast["periods"].append(
                {
                    "name": period["name"],
                    "start_time": period["startTime"],
                    "end_time": period["endTime"],
                    "temperature": period["temperature"],
                    "temperature_unit": period["temperatureUnit"],
                    "wind_speed": period["windSpeed"],
                    "wind_direction": period["windDirection"],
                    "short_forecast": period["shortForecast"],
                    "detailed_forecast": period["detailedForecast"],
                }
            )

        return forecast

    def get_current_conditions(self, lat: float, lon: float) -> Dict[str, Any]:
        """Get current weather conditions for a location."""
        # First get the grid point metadata
        point_data = self.get_point_metadata(lat, lon)

        # Then get the list of observation stations near this grid point
        grid_id = point_data["grid_id"]
        grid_x = point_data["grid_x"]
        grid_y = point_data["grid_y"]

        stations_data = self._request(
            f"gridpoints/{grid_id}/{grid_x},{grid_y}/stations"
        )

        # Get observations from the closest station
        if len(stations_data["features"]) > 0:
            station_id = stations_data["features"][0]["properties"]["stationIdentifier"]
            obs_data = self._request(f"stations/{station_id}/observations/latest")

            # Extract and simplify the relevant information
            props = obs_data["properties"]

            return {
                "station": station_id,
                "timestamp": props["timestamp"],
                "temperature": props["temperature"]["value"],
                "temperature_unit": "C",  # API returns in Celsius
                "humidity": props["relativeHumidity"]["value"],
                "wind_speed": props["windSpeed"]["value"],
                "wind_direction": props["windDirection"]["value"],
                "barometric_pressure": props["barometricPressure"]["value"],
                "description": props["textDescription"],
            }

        return {"error": "No observation stations found near this location"}


# Initialize the client
client = WeatherGovClient()


def require_params(*params):
    """Decorator to require specific query parameters."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            missing = [p for p in params if p not in request.args]
            if missing:
                return (
                    jsonify(
                        {"error": "Missing required parameters", "missing": missing}
                    ),
                    400,
                )
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def handle_api_errors(f):
    """Decorator to handle API errors."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            return (
                jsonify(
                    {
                        "error": "Weather.gov API error",
                        "status_code": e.response.status_code,
                        "message": str(e),
                    }
                ),
                500,
            )
        except Exception as e:
            return jsonify({"error": "Server error", "message": str(e)}), 500

    return decorated_function


@app.route("/api/weather/current", methods=["GET"])
@require_params("lat", "lon")
@handle_api_errors
def current_weather():
    """Get current weather conditions for a location."""
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))

    return jsonify(client.get_current_conditions(lat, lon))


@app.route("/api/weather/forecast", methods=["GET"])
@require_params("lat", "lon")
@handle_api_errors
def forecast():
    """Get forecast for a location."""
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))
    hourly = request.args.get("hourly", "false").lower() == "true"

    return jsonify(client.get_forecast(lat, lon, hourly))


@app.route("/api/weather/metadata", methods=["GET"])
@require_params("lat", "lon")
@handle_api_errors
def point_metadata():
    """Get point metadata for a location."""
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))

    return jsonify(client.get_point_metadata(lat, lon))


@app.route("/api/weather/summary", methods=["GET"])
@require_params("lat", "lon")
@handle_api_errors
def weather_summary():
    """Get a comprehensive weather summary for a location."""
    lat = float(request.args.get("lat"))
    lon = float(request.args.get("lon"))

    current = client.get_current_conditions(lat, lon)
    forecast_data = client.get_forecast(lat, lon)

    return jsonify(
        {
            "location": {"latitude": lat, "longitude": lon},
            "current": current,
            "forecast": forecast_data,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 42068))
    app.run(host="0.0.0.0", port=port)
