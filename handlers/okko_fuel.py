from typing import Any

from curl_cffi.requests import AsyncSession

API_URL = 'https://www.okko.ua/api/uk/fuels'


async def get_okko_fuel_price_a95() -> dict[str, Any]:
    """Fetch the current A-95 petrol price from the OKKO fuel API."""
    try:
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'uk-UA,uk;q=0.9,en;q=0.8',
            'Referer': 'https://www.okko.ua/',
        }
        async with AsyncSession(impersonate='chrome124') as session:
            response = await session.get(API_URL, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

        fuels = (
            data.get('data', {}).get('layout', [{}])[0]
            .get('data', {}).get('bullets', {}).get('items', [])
        )
        for fuel in fuels:
            if fuel.get('fuel_code') == 'A-95':
                return {
                    'success': True,
                    'station': 'ОККО',
                    'fuel': 'A-95',
                    'price': fuel.get('price'),
                    'currency': 'UAH',
                }

        return {'success': False, 'error': 'A-95 fuel not found in OKKO response'}

    except Exception as e:
        return {'success': False, 'error': str(e)}
