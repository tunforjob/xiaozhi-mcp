from typing import Any

import httpx

API_URL = 'https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json'
TARGET_CURRENCIES = ['USD', 'EUR', 'XAU']


def get_currency_rates() -> dict[str, Any]:
    """Get USD, EUR, and Gold rates from National Bank of Ukraine in UAH."""
    try:
        with httpx.Client() as client:
            response = client.get(API_URL)
            response.raise_for_status()
            all_rates: list[dict[str, Any]] = response.json()

        filtered_prices: dict[str, float] = {}
        exchange_date: str = ''

        for item in all_rates:
            currency_code = item.get('cc')

            if currency_code in TARGET_CURRENCIES:
                rate = item.get('rate')

                output_key = 'GOLD' if currency_code == 'XAU' else currency_code

                if isinstance(rate, (int, float)):
                    filtered_prices[output_key] = rate

                if not exchange_date:
                    exchange_date = item.get('exchangedate', 'N/A')

        return {'success': True, 'date': exchange_date, 'base_currency': 'UAH (Hryvnia)', 'rates': filtered_prices}

    except httpx.HTTPStatusError as e:
        return {'success': False, 'error': f'HTTP error (Status {e.response.status_code}): {e}'}
    except httpx.RequestError as e:
        return {'success': False, 'error': f'Request error (Network/DNS): {e}'}
    except Exception as e:
        return {'success': False, 'error': f'An unexpected error occurred: {e}'}
