"""
Grocery list CRUD wrapper for the Bring! API.

Simple wrapper that provides CRUD operations for grocery items
using the bring-api library.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import aiohttp
from bring_api import Bring, BringItemOperation
from bring_api.types import BringList


@dataclass
class GroceryItem:
    """Represents a grocery item."""

    name: str
    spec: str = ""
    uuid: str = field(default_factory=lambda: str(uuid4()))
    completed: bool = False

    def to_bring_dict(self) -> dict[str, str]:
        """Convert to Bring API format."""
        return {
            "itemId": self.name,
            "spec": self.spec,
            "uuid": self.uuid,
        }


class GroceryListCRUD:
    """
    CRUD wrapper for Bring! grocery lists.

    Provides simple Create, Read, Update, Delete operations
    for grocery items in a Bring! shopping list.
    """

    def __init__(self, email: str, password: str) -> None:
        """
        Initialize the grocery list CRUD.

        Args:
            email: Bring! account email
            password: Bring! account password
        """
        self.email = email
        self.password = password
        self._session: aiohttp.ClientSession | None = None
        self._bring: Bring | None = None
        self._list_uuid: str | None = None

    async def __aenter__(self) -> "GroceryListCRUD":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self) -> None:
        """Connect to Bring! API and login."""
        self._session = aiohttp.ClientSession()
        self._bring = Bring(self._session, self.email, self.password)
        await self._bring.login()

    async def disconnect(self) -> None:
        """Disconnect from Bring! API."""
        if self._session:
            await self._session.close()
            self._session = None
        self._bring = None

    @property
    def bring(self) -> Bring:
        """Get Bring instance, raising if not connected."""
        if self._bring is None:
            raise RuntimeError("Not connected. Call connect() first.")
        return self._bring

    async def get_lists(self) -> list[BringList]:
        """Get all available shopping lists."""
        result = await self.bring.load_lists()
        return result.lists

    async def set_list(self, list_uuid: str) -> None:
        """Set the active list by UUID."""
        self._list_uuid = list_uuid

    async def set_list_by_name(self, name: str) -> bool:
        """
        Set the active list by name.

        Returns True if found, False otherwise.
        """
        lists = await self.get_lists()
        for lst in lists:
            if lst.name.lower() == name.lower():
                self._list_uuid = lst.listUuid
                return True
        return False

    async def use_first_list(self) -> str | None:
        """Use the first available list. Returns list UUID or None."""
        lists = await self.get_lists()
        if lists:
            self._list_uuid = lists[0].listUuid
            return self._list_uuid
        return None

    @property
    def list_uuid(self) -> str:
        """Get current list UUID, raising if not set."""
        if self._list_uuid is None:
            raise RuntimeError("No list selected. Call set_list() first.")
        return self._list_uuid

    # ==================== CRUD Operations ====================

    async def create(self, name: str, spec: str = "") -> GroceryItem:
        """
        Create (add) a new grocery item to the list.

        Args:
            name: Item name (e.g., "Milk", "Bread")
            spec: Optional specification (e.g., "2L", "whole wheat")

        Returns:
            The created GroceryItem
        """
        item = GroceryItem(name=name, spec=spec)
        await self.bring.batch_update_list(
            self.list_uuid,
            item.to_bring_dict(),
            BringItemOperation.ADD,
        )
        return item

    async def read(self, name: str | None = None) -> list[GroceryItem]:
        """
        Read grocery items from the list.

        Args:
            name: Optional filter by item name

        Returns:
            List of GroceryItem objects
        """
        result = await self.bring.get_list(self.list_uuid)
        items: list[GroceryItem] = []

        # Process purchase items (not completed)
        for item_data in result.items.purchase:
            item = GroceryItem(
                name=item_data.itemId,
                spec=item_data.specification,
                uuid=item_data.uuid,
                completed=False,
            )
            if name is None or item.name.lower() == name.lower():
                items.append(item)

        # Process recently completed items
        for item_data in result.items.recently:
            item = GroceryItem(
                name=item_data.itemId,
                spec=item_data.specification,
                uuid=item_data.uuid,
                completed=True,
            )
            if name is None or item.name.lower() == name.lower():
                items.append(item)

        return items

    async def read_all(self) -> list[GroceryItem]:
        """Read all grocery items from the list."""
        return await self.read()

    async def read_pending(self) -> list[GroceryItem]:
        """Read only pending (not completed) items."""
        items = await self.read()
        return [item for item in items if not item.completed]

    async def read_completed(self) -> list[GroceryItem]:
        """Read only completed items."""
        items = await self.read()
        return [item for item in items if item.completed]

    async def update(self, item: GroceryItem) -> GroceryItem:
        """
        Update an existing grocery item.

        Args:
            item: GroceryItem with updated values

        Returns:
            The updated GroceryItem
        """
        await self.bring.batch_update_list(
            self.list_uuid,
            item.to_bring_dict(),
            BringItemOperation.ADD,
        )
        return item

    async def update_spec(self, name: str, new_spec: str) -> GroceryItem | None:
        """
        Update the specification of an item by name.

        Args:
            name: Item name to update
            new_spec: New specification

        Returns:
            Updated GroceryItem or None if not found
        """
        items = await self.read(name)
        if not items:
            return None

        item = items[0]
        item.spec = new_spec
        return await self.update(item)

    async def delete(self, item: GroceryItem) -> None:
        """
        Delete (remove) a grocery item from the list.

        Args:
            item: GroceryItem to remove
        """
        await self.bring.batch_update_list(
            self.list_uuid,
            item.to_bring_dict(),
            BringItemOperation.REMOVE,
        )

    async def delete_by_name(self, name: str) -> bool:
        """
        Delete an item by name.

        Args:
            name: Item name to delete

        Returns:
            True if deleted, False if not found
        """
        items = await self.read(name)
        if not items:
            return False

        await self.delete(items[0])
        return True

    async def complete(self, item: GroceryItem) -> None:
        """
        Mark a grocery item as completed.

        Args:
            item: GroceryItem to complete
        """
        await self.bring.batch_update_list(
            self.list_uuid,
            item.to_bring_dict(),
            BringItemOperation.COMPLETE,
        )
        item.completed = True

    async def complete_by_name(self, name: str) -> bool:
        """
        Complete an item by name.

        Args:
            name: Item name to complete

        Returns:
            True if completed, False if not found
        """
        items = await self.read(name)
        pending = [i for i in items if not i.completed]
        if not pending:
            return False

        await self.complete(pending[0])
        return True

    # ==================== Batch Operations ====================

    async def create_many(self, items: list[tuple[str, str]]) -> list[GroceryItem]:
        """
        Create multiple grocery items at once.

        Args:
            items: List of (name, spec) tuples

        Returns:
            List of created GroceryItem objects
        """
        grocery_items = [
            GroceryItem(name=name, spec=spec) for name, spec in items
        ]
        await self.bring.batch_update_list(
            self.list_uuid,
            [item.to_bring_dict() for item in grocery_items],
            BringItemOperation.ADD,
        )
        return grocery_items

    async def delete_many(self, items: list[GroceryItem]) -> None:
        """Delete multiple grocery items at once."""
        await self.bring.batch_update_list(
            self.list_uuid,
            [item.to_bring_dict() for item in items],
            BringItemOperation.REMOVE,
        )

    async def clear_completed(self) -> int:
        """
        Remove all completed items from the list.

        Returns:
            Number of items removed
        """
        completed = await self.read_completed()
        if completed:
            await self.delete_many(completed)
        return len(completed)


# ==================== Convenience Functions ====================


def run_async(coro: Any) -> Any:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


async def quick_add(
    email: str, password: str, items: list[str], list_name: str | None = None
) -> list[GroceryItem]:
    """
    Quickly add items to a grocery list.

    Args:
        email: Bring! account email
        password: Bring! account password
        items: List of item names to add
        list_name: Optional list name (uses first list if not provided)

    Returns:
        List of created GroceryItem objects
    """
    async with GroceryListCRUD(email, password) as grocery:
        if list_name:
            await grocery.set_list_by_name(list_name)
        else:
            await grocery.use_first_list()

        return await grocery.create_many([(item, "") for item in items])


# ==================== Example Usage ====================

if __name__ == "__main__":
    import os

    async def main() -> None:
        email = os.environ.get("BRING_EMAIL", "tunforall@gmail.com")
        password = os.environ.get("BRING_PASSWORD", "HW9IPySv")

        if not email or not password:
            print("Set BRING_EMAIL and BRING_PASSWORD environment variables")
            return

        async with GroceryListCRUD(email, password) as grocery:
            # Use first available list
            list_uuid = await grocery.use_first_list()
            print(f"Using list: {list_uuid}")

            # Create items
            milk = await grocery.create("Milk", "2L whole")
            bread = await grocery.create("Bread", "sourdough")
            print(f"Created: {milk.name}, {bread.name}")

            # Read all items
            all_items = await grocery.read_all()
            print(f"All items: {[i.name for i in all_items]}")

            # Update item
            milk.spec = "1L skim"
            await grocery.update(milk)
            print(f"Updated milk spec to: {milk.spec}")

            # Complete an item
            await grocery.complete(bread)
            print(f"Completed: {bread.name}")

            # Read pending items
            pending = await grocery.read_pending()
            print(f"Pending: {[i.name for i in pending]}")

            # Delete an item
            await grocery.delete(milk)
            print(f"Deleted: {milk.name}")

    asyncio.run(main())
