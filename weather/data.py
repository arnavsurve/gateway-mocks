registry_data = {
    "name": "Weather API",
    "description": "Weather forecasting service using Weather.gov data",
    "url": "http://localhost:42068",
    "capabilities": {"tools": False, "resources": False, "prompts": False},
    "categories": ["weather", "forecasting", "api"],
    "metadata": {
        "version": "1.0",
        "provider": "Weather.gov",
        "implementation": "Flask",
    },
    "api_docs": """# Weather API Documentation

This API provides weather data from the National Weather Service (weather.gov).

## Endpoints

### Get Current Weather
GET /api/weather/current

Parameters:
- lat (required): Latitude as a decimal number (e.g., 38.8894)
- lon (required): Longitude as a decimal number (e.g., -77.0353)

Returns current weather conditions including temperature, humidity, wind speed, and textual description.

Example:
GET /api/weather/current?lat=38.8894&lon=-77.0353

### Get Weather Forecast
GET /api/weather/forecast

Parameters:
- lat (required): Latitude as a decimal number
- lon (required): Longitude as a decimal number
- hourly (optional): Set to "true" for hourly forecast, "false" (default) for daily forecast

Returns a multi-period forecast with temperature, wind conditions, and detailed descriptions.

Example:
GET /api/weather/forecast?lat=38.8894&lon=-77.0353
GET /api/weather/forecast?lat=38.8894&lon=-77.0353&hourly=true

### Get Point Metadata
GET /api/weather/metadata

Parameters:
- lat (required): Latitude as a decimal number
- lon (required): Longitude as a decimal number

Returns metadata about the forecast grid point for the requested location.

Example:
GET /api/weather/metadata?lat=38.8894&lon=-77.0353

### Get Weather Summary
GET /api/weather/summary

Parameters:
- lat (required): Latitude as a decimal number
- lon (required): Longitude as a decimal number

Provides a comprehensive summary including both current conditions and forecast.

Example:
GET /api/weather/summary?lat=38.8894&lon=-77.0353

## Common Locations

- New York, NY: lat=40.7128, lon=-74.0060
- Los Angeles, CA: lat=34.0522, lon=-118.2437
- Chicago, IL: lat=41.8781, lon=-87.6298
- Houston, TX: lat=29.7604, lon=-95.3698
- Phoenix, AZ: lat=33.4484, lon=-112.0740

## Error Handling

If required parameters are missing, the API will return a 400 status with an error message.
Weather.gov API errors will result in a 500 status with detailed error information.""",
}
