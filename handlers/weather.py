import os
from typing import Any

import httpx

API_KEY = os.getenv('OPENWEATHER_API_KEY')
BASE_URL = 'https://api.openweathermap.org/data/2.5/weather'


async def get_weather(city: str) -> dict[str, Any]:
    """Fetch weather data for a city from OpenWeatherMap API."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            BASE_URL,
            params={
                'q': city,
                'appid': API_KEY,
                'units': 'metric',
                'lang': 'ru',
            },
        )
        response.raise_for_status()
        data = response.json()

    return {
        'city': data['name'],
        'temp': data['main']['temp'],
        'feels_like': data['main']['feels_like'],
        'humidity': data['main']['humidity'],
        'weather': data['weather'][0]['description'],
        'wind': data['wind']['speed'],
    }
