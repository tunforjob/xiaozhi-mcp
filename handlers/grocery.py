"""Grocery list handlers using Bring! API."""
import os
from typing import Any, Dict, List

from grocery import GroceryListCRUD, GroceryItem

# Global instance to maintain connection
_grocery_crud: GroceryListCRUD | None = None


async def _get_grocery_crud() -> GroceryListCRUD:
    """Get or create the grocery CRUD instance."""
    global _grocery_crud
    
    if _grocery_crud is None:
        email = os.environ.get("BRING_EMAIL")
        password = os.environ.get("BRING_PASSWORD")
        
        if not email or not password:
            raise ValueError("BRING_EMAIL and BRING_PASSWORD environment variables must be set")
        
        _grocery_crud = GroceryListCRUD(email, password)
        await _grocery_crud.connect()
        await _grocery_crud.use_first_list()
    
    return _grocery_crud


async def add_grocery_item(name: str, spec: str = "") -> Dict[str, Any]:
    """Add a grocery item to the list."""
    grocery = await _get_grocery_crud()
    item = await grocery.create(name, spec)
    
    return {
        "status": "ok",
        "added": {
            "name": item.name,
            "spec": item.spec,
            "uuid": item.uuid,
        },
    }


async def remove_grocery_item(name: str) -> Dict[str, Any]:
    """Remove a grocery item from the list by name."""
    grocery = await _get_grocery_crud()
    success = await grocery.delete_by_name(name)
    
    if not success:
        return {"status": "error", "message": "Item not found"}
    
    return {
        "status": "ok",
        "removed": name,
    }


async def list_grocery_items() -> Dict[str, List[Dict[str, Any]]]:
    """Return the full list of grocery items."""
    grocery = await _get_grocery_crud()
    items = await grocery.read_all()
    
    return {
        "items": [
            {
                "name": item.name,
                "spec": item.spec,
                "uuid": item.uuid,
                "completed": item.completed,
            }
            for item in items
        ]
    }


async def complete_grocery_item(name: str) -> Dict[str, Any]:
    """Mark a grocery item as completed."""
    grocery = await _get_grocery_crud()
    success = await grocery.complete_by_name(name)
    
    if not success:
        return {"status": "error", "message": "Item not found or already completed"}
    
    return {
        "status": "ok",
        "completed": name,
    }


async def update_grocery_spec(name: str, new_spec: str) -> Dict[str, Any]:
    """Update the specification of a grocery item."""
    grocery = await _get_grocery_crud()
    item = await grocery.update_spec(name, new_spec)
    
    if item is None:
        return {"status": "error", "message": "Item not found"}
    
    return {
        "status": "ok",
        "updated": {
            "name": item.name,
            "spec": item.spec,
        },
    }
