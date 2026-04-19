import logging
import os
import sys
import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastmcp import FastMCP

from handlers import (
    add_grocery_item,
    calculate,
    complete_grocery_item,
    get_crypto_prices,
    get_okko_fuel_price_a95,
    get_currency_rates,
    get_products_list,
    get_weather,
    get_weather_plan,
    list_grocery_items,
    remove_grocery_item,
    update_grocery_spec,
)
from handlers import (
    add_product as handler_add_product,
)
from handlers import (
    list_products as handler_list_products,
)
from handlers import (
    remove_product as handler_remove_product,
)

logger = logging.getLogger('MyMCP')

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')



# Create an MCP server
mcp = FastMCP('MyMCP')


@mcp.tool()
def calculator(python_expression: str) -> dict[str, Any]:
    """For mathematical calculation, always use this tool to calculate the result of a python expression. You can use 'math' or 'random' directly, without 'import'."""
    logger.info(f'Calculating formula: {python_expression}')
    result = calculate(python_expression)
    logger.info(f'Result: {result}')
    return result


if os.getenv('OPENWEATHER_API_KEY'):

    @mcp.tool()
    async def weather(city: str) -> dict[str, Any]:
        """Get current weather by city name. Always use english name of the city. Default city is Kharkiv."""
        logger.info(f'Getting weather for {city}')
        result = await get_weather(city)
        logger.info(f'Weather fetched: city={result.get("city")}, temp={result.get("temp")}°C')
        return result

    @mcp.tool()
    async def weather_plan(city: str, days: int = 5) -> dict[str, Any]:
        """
        Get a multi-day weather plan to help decide when to go outside and what to wear.
        Returns a per-day forecast with:
          - go_outside_score (0–10): how good the day is for outdoor activities
          - verdict: human-readable recommendation (go out / stay home)
          - what_to_wear: clothing advice based on temperature, wind, rain/snow
          - temp_min / temp_max / temp_avg, humidity, wind speed, precipitation probability
        Also highlights the best and worst days of the period.
        Always use english city name. Default city is Kharkiv. Max days = 5 (free API tier).
        """
        logger.info(f'Getting weather plan for {city}, {days} days')
        result = await get_weather_plan(city, days)
        logger.info(
            f'Weather plan fetched: city={result.get("city")}, '
            f'best_day={result.get("best_day")}, worst_day={result.get("worst_day")}'
        )
        return result

else:
    logger.warning('OPENWEATHER_API_KEY not found. Weather tool disabled.')


@mcp.tool(name='add_product', description='Add a product name to the in-memory product list.')
def add_product(name: str) -> dict[str, Any]:
    logger.info(f'Adding product: {name}')
    result = handler_add_product(name)
    logger.info(f'Product added. total_products={result.get("total_products")}')
    return result


@mcp.tool(name='remove_product', description='Remove a product from the list by its name. Returns error if not found.')
def remove_product(name: str) -> dict[str, Any]:
    logger.info(f'Removing product: {name}')
    result = handler_remove_product(name)
    if result.get('status') == 'error':
        logger.warning(f'Product not found: {name}')
    else:
        logger.info(f'Product removed: {name}. total_products={result.get("total_products")}')
    return result


@mcp.tool(name='list_products', description='Return the full list of currently stored product names.')
def list_products() -> dict[str, list[str]]:
    products = get_products_list()
    logger.info(f'Listing products: count={len(products)}')
    return handler_list_products()


@mcp.tool(
    name='get_okko_fuel_price_a95',
    description='Returns the current price of A-95 gasoline at OKKO gas stations in Ukrainian hryvnias (UAH).',
)
async def okko_fuel_price_a95() -> dict[str, Any]:
    """Get current A-95 petrol price at OKKO fuel stations."""
    logger.info('Fetching OKKO A-95 fuel price')
    result = await get_okko_fuel_price_a95()
    if result.get('success'):
        logger.info(f'OKKO A-95 price: {result.get("price")} UAH')
    else:
        logger.warning(f'OKKO fuel fetch failed: {result.get("error")}')
    return result


@mcp.tool(
    name='get_crypto_prices',
    description='Gets current Bitcoin, Ethereum, and Solana exchange rates to the US dollar (USD) using the CoinGecko API.',
)
def crypto_prices() -> dict[str, Any]:
    """Gets current Bitcoin, Ethereum, and Solana exchange rates to USD."""
    logger.info('Fetching crypto prices')
    return get_crypto_prices()


@mcp.tool(
    name='get_currency_rates',
    description='Retrieves the current official exchange rates for USD, EUR, and Gold from the National Bank of Ukraine in UAH.',
)
def currency_rates() -> dict[str, Any]:
    """Get USD, EUR, and Gold rates from NBU."""
    result = get_currency_rates()
    logger.info(f'NBU rates received: {result.get("rates")}')
    return result


if os.getenv('BRING_EMAIL') and os.getenv('BRING_PASSWORD'):

    @mcp.tool(
        name='add_grocery_item',
        description='Add a grocery item to the Bring! shopping list with optional specification.',
    )
    async def add_grocery(name: str, spec: str = '') -> dict[str, Any]:
        """Add a grocery item to the shopping list."""
        logger.info(f'Adding grocery item: {name} (spec: {spec})')
        result = await add_grocery_item(name, spec)
        logger.info(f'Grocery item added: {result}')
        return result

    @mcp.tool(name='remove_grocery_item', description='Remove a grocery item from the Bring! shopping list by name.')
    async def remove_grocery(name: str) -> dict[str, Any]:
        """Remove a grocery item from the shopping list."""
        logger.info(f'Removing grocery item: {name}')
        result = await remove_grocery_item(name)
        if result.get('status') == 'error':
            logger.warning(f'Grocery item not found: {name}')
        else:
            logger.info(f'Grocery item removed: {name}')
        return result

    @mcp.tool(
        name='list_grocery_items',
        description='List all grocery items in the Bring! shopping list, including completed items.',
    )
    async def list_groceries() -> dict[str, Any]:
        """List all grocery items."""
        logger.info('Listing all grocery items')
        result = await list_grocery_items()
        logger.info(f'Found {len(result.get("items", []))} grocery items')
        return result

    @mcp.tool(name='complete_grocery_item', description='Mark a grocery item as completed in the Bring! shopping list.')
    async def complete_grocery(name: str) -> dict[str, Any]:
        """Mark a grocery item as completed."""
        logger.info(f'Completing grocery item: {name}')
        result = await complete_grocery_item(name)
        if result.get('status') == 'error':
            logger.warning(f'Could not complete item: {name}')
        else:
            logger.info(f'Grocery item completed: {name}')
        return result

    @mcp.tool(
        name='update_grocery_spec', description='Update the specification of a grocery item in the Bring! shopping list.'
    )
    async def update_grocery(name: str, new_spec: str) -> dict[str, Any]:
        """Update a grocery item's specification."""
        logger.info(f'Updating grocery item spec: {name} -> {new_spec}')
        result = await update_grocery_spec(name, new_spec)
        if result.get('status') == 'error':
            logger.warning(f'Could not update item: {name}')
        else:
            logger.info(f'Grocery item updated: {result}')
        return result
else:
    logger.warning('BRING_EMAIL or BRING_PASSWORD not found. Grocery list tools disabled.')


_GCAL_CREDENTIALS = Path.home() / '.config' / 'xiaozhi' / 'credentials.json'
_GCAL_TOKEN = Path.home() / '.config' / 'xiaozhi' / 'token.json'

if _GCAL_CREDENTIALS.exists() or os.getenv('GOOGLE_CALENDAR_API_KEY'):
    from xiaozhi_mcp.calendar import GoogleCalendarClient

    @mcp.tool(
        name='list_google_calendars',
        description='List all Google Calendars the user has access to. Returns id, name and whether it is primary.',
    )
    async def list_google_calendars() -> dict[str, Any]:
        logger.info('Listing Google Calendars')
        async with GoogleCalendarClient() as client:
            calendars = await client.get_calendars()
        logger.info(f'Found {len(calendars)} calendars')
        return {
            'calendars': [
                {'id': cal.id, 'name': cal.summary, 'primary': cal.primary, 'access_role': cal.access_role}
                for cal in calendars
            ]
        }

    @mcp.tool(
        name='get_google_calendar_events',
        description=(
            'Get events from a Google Calendar for a given time period. '
            'calendar_name: calendar name (empty = primary calendar). '
            'date_from / date_to: ISO date strings like "2026-04-15" (default: today → +7 days). '
            'days: shortcut — number of days ahead from today (used only when date_to is empty).'
        ),
    )
    async def get_google_calendar_events(
        calendar_name: str = '',
        date_from: str = '',
        date_to: str = '',
        days: int = 7,
    ) -> dict[str, Any]:
        time_min = datetime.fromisoformat(date_from).replace(tzinfo=UTC) if date_from else datetime.now(UTC)
        time_max = datetime.fromisoformat(date_to).replace(tzinfo=UTC) if date_to else time_min + timedelta(days=days)

        async with GoogleCalendarClient() as client:
            if calendar_name:
                all_cals = await client.get_calendars()
                cal = next((c for c in all_cals if c.summary.lower() == calendar_name.lower()), None)
                if cal is None:
                    return {'status': 'error', 'message': f'Calendar "{calendar_name}" not found'}
                calendar_id = cal.id
            else:
                calendar_id = 'primary'

            logger.info(f'Fetching events: calendar={calendar_id}, {time_min.date()} → {time_max.date()}')
            events = await client.get_events(calendar_id=calendar_id, time_min=time_min, time_max=time_max)

        logger.info(f'Found {len(events)} events')
        return {
            'calendar': calendar_name or 'primary',
            'date_from': time_min.date().isoformat(),
            'date_to': time_max.date().isoformat(),
            'count': len(events),
            'events': [
                {
                    'date': e.start.strftime('%Y-%m-%d') if e.all_day else e.start.strftime('%Y-%m-%d %H:%M'),
                    'title': e.summary,
                    'location': e.location,
                    'description': e.description,
                    'all_day': e.all_day,
                }
                for e in events
            ],
        }

else:
    logger.warning('Google Calendar credentials not found. Calendar tools disabled.')


if os.getenv('O365_CLIENT_ID') and os.getenv('O365_CLIENT_SECRET'):
    from xiaozhi_mcp.outlook_calendar import OutlookCalendarClient

    @mcp.tool(
        name='list_outlook_calendars',
        description='List all Microsoft Outlook / Teams calendars the user has access to. Returns id, name and whether it is the default calendar.',
    )
    async def list_outlook_calendars() -> dict[str, Any]:
        logger.info('Listing Outlook calendars')
        async with OutlookCalendarClient() as client:
            calendars = await client.get_calendars()
        logger.info(f'Found {len(calendars)} Outlook calendars')
        return {
            'calendars': [
                {'id': cal.id, 'name': cal.name, 'is_default': cal.is_default}
                for cal in calendars
            ]
        }

    @mcp.tool(
        name='get_outlook_calendar_events',
        description=(
            'Get events from a Microsoft Outlook / Teams calendar for a given time period. '
            'calendar_id: calendar ID from list_outlook_calendars (empty = default calendar). '
            'date_from / date_to: ISO date strings like "2026-04-15" (default: today → +7 days). '
            'days: shortcut — number of days ahead from today (used only when date_to is empty). '
            'Returns subject, start/end times, location, Teams meeting link, and organizer.'
        ),
    )
    async def get_outlook_calendar_events(
        calendar_id: str = '',
        date_from: str = '',
        date_to: str = '',
        days: int = 7,
    ) -> dict[str, Any]:
        time_min = datetime.fromisoformat(date_from).replace(tzinfo=UTC) if date_from else datetime.now(UTC)
        time_max = datetime.fromisoformat(date_to).replace(tzinfo=UTC) if date_to else time_min + timedelta(days=days)

        logger.info(f'Fetching Outlook events: calendar={calendar_id or "default"}, {time_min.date()} → {time_max.date()}')
        async with OutlookCalendarClient() as client:
            events = await client.get_events(
                calendar_id=calendar_id or None,
                time_min=time_min,
                time_max=time_max,
            )

        logger.info(f'Found {len(events)} Outlook events')
        return {
            'calendar': calendar_id or 'default',
            'date_from': time_min.date().isoformat(),
            'date_to': time_max.date().isoformat(),
            'count': len(events),
            'events': [
                {
                    'date': e.start.strftime('%Y-%m-%d') if e.all_day else e.start.strftime('%Y-%m-%d %H:%M'),
                    'title': e.subject,
                    'location': e.location,
                    'organizer': e.organizer,
                    'is_online_meeting': e.is_online_meeting,
                    'teams_link': e.teams_link,
                    'description': e.description,
                    'all_day': e.all_day,
                }
                for e in events
            ],
        }

else:
    logger.warning('O365_CLIENT_ID or O365_CLIENT_SECRET not found. Outlook Calendar tools disabled.')


async def list_tools_on_startup():
    """List all available tools on startup."""
    tools = await mcp.get_tools()
    logger.info(f'Found {len(tools)} tools:')
    if isinstance(tools, dict):
        for name, tool in tools.items():
            logger.info(f' - {name}: {tool.description}')
    elif isinstance(tools, list):
        for tool in tools:
            logger.info(f' - {tool.name}: {tool.description}')


# Start the server
if __name__ == '__main__':
    asyncio.run(list_tools_on_startup())
    mcp.run(transport='stdio')
