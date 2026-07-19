"""Weather plugin: Open-Meteo, no API key required."""

import asyncio

from claude_agent_sdk import tool

WMO = {
    0: "clear sky", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "rime fog", 51: "light drizzle", 53: "drizzle",
    55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers",
    81: "rain showers", 82: "violent rain showers", 85: "snow showers",
    86: "snow showers", 95: "thunderstorm", 96: "thunderstorm with hail",
    99: "thunderstorm with heavy hail",
}


def _get_weather(city: str) -> str:
    import requests

    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1}, timeout=10,
    ).json()
    if not geo.get("results"):
        return f"Could not find a place called {city}."
    loc = geo["results"][0]

    wx = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": loc["latitude"], "longitude": loc["longitude"],
            "current": "temperature_2m,apparent_temperature,weather_code,"
                       "wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "forecast_days": 3, "timezone": "auto",
        }, timeout=10,
    ).json()

    cur = wx["current"]
    lines = [
        f"Weather in {loc['name']}, {loc.get('country', '')}:",
        f"Now: {cur['temperature_2m']}C (feels {cur['apparent_temperature']}C), "
        f"{WMO.get(cur['weather_code'], 'unknown')}, wind {cur['wind_speed_10m']} km/h",
    ]
    daily = wx["daily"]
    for i, day in enumerate(daily["time"]):
        lines.append(
            f"{day}: {daily['temperature_2m_min'][i]}-{daily['temperature_2m_max'][i]}C, "
            f"{WMO.get(daily['weather_code'][i], 'unknown')}"
        )
    return "\n".join(lines)


@tool("get_weather", "Get current weather and a 3-day forecast for a city.",
      {"city": str})
async def get_weather(args: dict) -> dict:
    text = await asyncio.to_thread(_get_weather, args["city"])
    return {"content": [{"type": "text", "text": text}]}


TOOLS = [get_weather]
