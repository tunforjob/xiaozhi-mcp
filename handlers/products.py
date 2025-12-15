from typing import Any

# In-memory product storage
PRODUCTS: list[str] = []


def add_product(name: str) -> dict[str, Any]:
    """Add a product to the in-memory list."""
    PRODUCTS.append(name)
    return {
        'status': 'ok',
        'added': name,
        'total_products': len(PRODUCTS),
    }


def remove_product(name: str) -> dict[str, Any]:
    """Remove a product from the list by name."""
    if name not in PRODUCTS:
        return {'status': 'error', 'message': 'Product not found'}

    PRODUCTS.remove(name)
    return {
        'status': 'ok',
        'removed': name,
        'total_products': len(PRODUCTS),
    }


def list_products() -> dict[str, list[str]]:
    """Return the full list of products."""
    return {'products': PRODUCTS}


def get_products_list() -> list[str]:
    """Get reference to the products list (for external registration)."""
    return PRODUCTS
