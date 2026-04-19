import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import httpx

API_KEY = os.getenv('OPENWEATHER_API_KEY')
BASE_URL = 'https://api.openweathermap.org/data/2.5/weather'
FORECAST_URL = 'https://api.openweathermap.org/data/2.5/forecast'
ONE_CALL_URL = 'https://api.openweathermap.org/data/3.0/onecall'
GEOCODING_URL = 'https://api.openweathermap.org/geo/1.0/direct'


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


async def get_weather_forecast(city: str, days: int = 5) -> list[dict[str, Any]]:
    """
    Fetch 5-day weather forecast (free tier) with 3-hour step.
    Results are grouped by day. Max 5 days.

    Uses: GET /data/2.5/forecast
    Docs: https://openweathermap.org/forecast5
    """
    days = max(1, min(days, 5))

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            FORECAST_URL,
            params={
                'q': city,
                'appid': API_KEY,
                'units': 'metric',
                'lang': 'ru',
                'cnt': days * 8,  # 8 timestamps per day (3h step)
            },
        )
        response.raise_for_status()
        data = response.json()

    # Group 3-hour slots by calendar date
    daily: dict[str, list] = defaultdict(list)
    for entry in data['list']:
        date = entry['dt_txt'].split(' ')[0]  # "YYYY-MM-DD"
        daily[date].append(entry)

    result = []
    for date, slots in sorted(daily.items()):
        temps = [s['main']['temp'] for s in slots]
        humidities = [s['main']['humidity'] for s in slots]
        winds = [s['wind']['speed'] for s in slots]
        # pick the midday slot (or first available) for weather description
        midday = next((s for s in slots if '12:00:00' in s['dt_txt']), slots[0])

        result.append({
            'date': date,
            'temp_min': round(min(temps), 1),
            'temp_max': round(max(temps), 1),
            'temp_avg': round(sum(temps) / len(temps), 1),
            'humidity': round(sum(humidities) / len(humidities)),
            'wind': round(sum(winds) / len(winds), 1),
            'weather': midday['weather'][0]['description'],
            'pop': round(max(s.get('pop', 0) for s in slots) * 100),  # precipitation probability %
        })

    return result[:days]


async def get_weather_forecast_onecall(lat: float, lon: float, days: int = 7) -> list[dict[str, Any]]:
    """
    Fetch up to 8-day daily forecast via One Call API 3.0 (requires paid subscription).

    Uses: GET /data/3.0/onecall
    Docs: https://openweathermap.org/api/one-call-3
    """
    days = max(1, min(days, 8))

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            ONE_CALL_URL,
            params={
                'lat': lat,
                'lon': lon,
                'appid': API_KEY,
                'units': 'metric',
                'lang': 'ru',
                'exclude': 'current,minutely,hourly,alerts',  # only daily
            },
        )
        response.raise_for_status()
        data = response.json()

    result = []
    for day in data.get('daily', [])[:days]:
        dt = datetime.fromtimestamp(day['dt'], tz=timezone.utc)
        result.append({
            'date': dt.strftime('%Y-%m-%d'),
            'temp_min': day['temp']['min'],
            'temp_max': day['temp']['max'],
            'temp_day': day['temp']['day'],
            'temp_night': day['temp']['night'],
            'feels_like_day': day['feels_like']['day'],
            'humidity': day['humidity'],
            'wind': day['wind_speed'],
            'weather': day['weather'][0]['description'],
            'pop': round(day.get('pop', 0) * 100),  # precipitation probability %
            'uvi': day.get('uvi'),
            'summary': day.get('summary', ''),
        })

    return result


async def get_coords_by_city(city: str) -> tuple[float, float]:
    """
    Convert city name to lat/lon using OpenWeather Geocoding API.
    Needed for One Call API 3.0.

    Uses: GET /geo/1.0/direct
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            GEOCODING_URL,
            params={'q': city, 'limit': 1, 'appid': API_KEY},
        )
        response.raise_for_status()
        data = response.json()

    if not data:
        raise ValueError(f"City '{city}' not found")

    return data[0]['lat'], data[0]['lon']


def _make_day_plan(day: dict[str, Any]) -> dict[str, Any]:
    """
    Analyse a single day forecast dict and return planning advice:
    go_outside score (0-10), recommendation, what_to_wear.
    """
    temp_max = day['temp_max']
    temp_min = day['temp_min']
    temp_avg = day['temp_avg']
    wind = day['wind']
    pop = day['pop']  # precipitation probability %
    description = day['weather'].lower()

    # --- Go-outside score (0 = terrible, 10 = perfect) ---
    score = 10

    # Rain / snow / storm penalty
    bad_conditions = ('гроза', 'ливень', 'снег', 'метель', 'туман', 'шторм', 'дождь')
    for cond in bad_conditions:
        if cond in description:
            score -= 3
            break
    if pop >= 70:
        score -= 2
    elif pop >= 40:
        score -= 1

    # Wind penalty
    if wind >= 15:
        score -= 2
    elif wind >= 10:
        score -= 1

    # Temperature penalty
    if temp_max < -10 or temp_max > 38:
        score -= 3
    elif temp_max < 0 or temp_max > 33:
        score -= 2
    elif temp_max < 5 or temp_max > 30:
        score -= 1

    score = max(0, min(10, score))

    # --- Verdict ---
    if score >= 8:
        verdict = '✅ Отличный день — смело выходи на улицу!'
    elif score >= 6:
        verdict = '🟡 Неплохой день, но возьми зонт или куртку.'
    elif score >= 4:
        verdict = '🟠 Погода посредственная — одевайся теплее и внимательно.'
    elif score >= 2:
        verdict = '🔴 Лучше остаться дома или выйти ненадолго.'
    else:
        verdict = '❌ Плохая погода — сиди дома!'

    # --- Clothing ---
    wear = []
    if temp_avg < 0:
        wear.append('Тёплый зимний пуховик, шапка, шарф, тёплые перчатки, зимние ботинки')
    elif temp_avg < 8:
        wear.append('Зимнее пальто или пуховик, шапка, перчатки')
    elif temp_avg < 14:
        wear.append('Тёплая куртка или плащ, свитер')
    elif temp_avg < 18:
        wear.append('Лёгкая куртка или толстовка')
    elif temp_avg < 24:
        wear.append('Футболка + лёгкий слой (кофта или лёгкая куртка)')
    else:
        wear.append('Лёгкая летняя одежда, футболка')

    if any(c in description for c in ('дождь', 'ливень', 'гроза', 'морось')):
        wear.append('☂️ Зонт или дождевик, водонепроницаемая обувь')
    elif pop >= 40:
        wear.append('☂️ Возьми зонт — вероятность дождя высокая')

    if any(c in description for c in ('снег', 'метель')):
        wear.append('❄️ Зимние ботинки с нескользящей подошвой')

    if wind >= 10:
        wear.append('🌬️ Ветрозащитная куртка или ветровка')

    if temp_max >= 28:
        wear.append('🕶️ Солнцезащитные очки, лёгкий головной убор')

    return {
        **day,
        'go_outside_score': score,
        'verdict': verdict,
        'what_to_wear': '; '.join(wear),
    }


async def get_weather_plan(city: str, days: int = 5) -> dict[str, Any]:
    """
    Get a day/week planning forecast for a city.
    Returns per-day clothing advice and go-outside recommendation.
    Uses free-tier /data/2.5/forecast endpoint (max 5 days).
    """
    forecast = await get_weather_forecast(city, days)
    plan = [_make_day_plan(day) for day in forecast]

    best_day = max(plan, key=lambda d: d['go_outside_score'])
    worst_day = min(plan, key=lambda d: d['go_outside_score'])

    return {
        'city': city,
        'days': plan,
        'best_day': best_day['date'],
        'worst_day': worst_day['date'],
    }
