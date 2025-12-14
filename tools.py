# server.py
import logging
import sys
from typing import Any, Dict, List

from fastmcp import FastMCP
from pydantic import BaseModel

from handlers import (
    calculate,
    get_crypto_prices,
    get_currency_rates,
    get_weather,
    add_product as handler_add_product,
    remove_product as handler_remove_product,
    list_products as handler_list_products,
    get_products_list,
    add_grocery_item,
    remove_grocery_item,
    list_grocery_items,
    complete_grocery_item,
    update_grocery_spec,
)

logger = logging.getLogger('MyMCP')

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class AddProductInput(BaseModel):
    name: str


class RemoveProductInput(BaseModel):
    name: str


class AddGroceryInput(BaseModel):
    name: str
    spec: str = ""


class RemoveGroceryInput(BaseModel):
    name: str


class CompleteGroceryInput(BaseModel):
    name: str


class UpdateGrocerySpecInput(BaseModel):
    name: str
    new_spec: str


# Create an MCP server
mcp = FastMCP("MyMCP")


@mcp.tool()
def calculator(python_expression: str) -> Dict[str, Any]:
    """For mathematical calculation, always use this tool to calculate the result of a python expression. You can use 'math' or 'random' directly, without 'import'."""
    logger.info(f"Calculating formula: {python_expression}")
    result = calculate(python_expression)
    logger.info(f"Result: {result}")
    return result


@mcp.tool()
async def weather(city: str) -> Dict[str, Any]:
    """Get weather by name of the city. Always use english name of the city. Default city is Kharkiv."""
    logger.info(f"Getting weather for {city}")
    result = await get_weather(city)
    logger.info(f"Weather fetched: city={result.get('city')}, temp={result.get('temp')}°C")
    return result


@mcp.tool(
    name="add_product",
    description="Add a product name to the in-memory product list."
)
def add_product(data: AddProductInput) -> Dict[str, Any]:
    logger.info(f"Adding product: {data.name}")
    result = handler_add_product(data.name)
    logger.info(f"Product added. total_products={result.get('total_products')}")
    return result


@mcp.tool(
    name="remove_product",
    description="Remove a product from the list by its name. Returns error if not found."
)
def remove_product(data: RemoveProductInput) -> Dict[str, Any]:
    logger.info(f"Removing product: {data.name}")
    result = handler_remove_product(data.name)
    if result.get("status") == "error":
        logger.warning(f"Product not found: {data.name}")
    else:
        logger.info(f"Product removed: {data.name}. total_products={result.get('total_products')}")
    return result


@mcp.tool(
    name="list_products",
    description="Return the full list of currently stored product names."
)
def list_products() -> Dict[str, List[str]]:
    products = get_products_list()
    logger.info(f"Listing products: count={len(products)}")
    return handler_list_products()


@mcp.tool(
    name='get_crypto_prices',
    description='Gets current Bitcoin, Ethereum, and Solana exchange rates to the US dollar (USD) using the CoinGecko API.'
)
def crypto_prices() -> Dict[str, Any]:
    """Gets current Bitcoin, Ethereum, and Solana exchange rates to USD."""
    logger.info("Fetching crypto prices")
    return get_crypto_prices()


@mcp.tool(
    name='get_currency_rates',
    description='Retrieves the current official exchange rates for USD, EUR, and Gold from the National Bank of Ukraine in UAH.'
)
def currency_rates() -> Dict[str, Any]:
    """Get USD, EUR, and Gold rates from NBU."""
    result = get_currency_rates()
    logger.info(f"NBU rates received: {result.get('rates')}")
    return result


@mcp.tool(
    name="add_grocery_item",
    description="Add a grocery item to the Bring! shopping list with optional specification."
)
async def add_grocery(data: AddGroceryInput) -> Dict[str, Any]:
    """Add a grocery item to the shopping list."""
    logger.info(f"Adding grocery item: {data.name} (spec: {data.spec})")
    result = await add_grocery_item(data.name, data.spec)
    logger.info(f"Grocery item added: {result}")
    return result


@mcp.tool(
    name="remove_grocery_item",
    description="Remove a grocery item from the Bring! shopping list by name."
)
async def remove_grocery(data: RemoveGroceryInput) -> Dict[str, Any]:
    """Remove a grocery item from the shopping list."""
    logger.info(f"Removing grocery item: {data.name}")
    result = await remove_grocery_item(data.name)
    if result.get("status") == "error":
        logger.warning(f"Grocery item not found: {data.name}")
    else:
        logger.info(f"Grocery item removed: {data.name}")
    return result


@mcp.tool(
    name="list_grocery_items",
    description="List all grocery items in the Bring! shopping list, including completed items."
)
async def list_groceries() -> Dict[str, Any]:
    """List all grocery items."""
    logger.info("Listing all grocery items")
    result = await list_grocery_items()
    logger.info(f"Found {len(result.get('items', []))} grocery items")
    return result


@mcp.tool(
    name="complete_grocery_item",
    description="Mark a grocery item as completed in the Bring! shopping list."
)
async def complete_grocery(data: CompleteGroceryInput) -> Dict[str, Any]:
    """Mark a grocery item as completed."""
    logger.info(f"Completing grocery item: {data.name}")
    result = await complete_grocery_item(data.name)
    if result.get("status") == "error":
        logger.warning(f"Could not complete item: {data.name}")
    else:
        logger.info(f"Grocery item completed: {data.name}")
    return result


@mcp.tool(
    name="update_grocery_spec",
    description="Update the specification of a grocery item in the Bring! shopping list."
)
async def update_grocery(data: UpdateGrocerySpecInput) -> Dict[str, Any]:
    """Update a grocery item's specification."""
    logger.info(f"Updating grocery item spec: {data.name} -> {data.new_spec}")
    result = await update_grocery_spec(data.name, data.new_spec)
    if result.get("status") == "error":
        logger.warning(f"Could not update item: {data.name}")
    else:
        logger.info(f"Grocery item updated: {result}")
    return result


# Start the server
if __name__ == "__main__":
    mcp.run(transport="stdio")
