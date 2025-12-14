"""Telegram messaging module using Pyrogram.

This module provides functionality to:
- Get list of Telegram contacts
- Send messages to allowed contacts only
"""

import json
import logging
from pathlib import Path
from typing import Optional

from pyrogram import Client
from pyrogram.types import User as TgUser

logger = logging.getLogger(__name__)


class TelegramClient:
    """Telegram client for sending messages and managing contacts."""

    def __init__(self, config_path: str = "telegram_config.json"):
        """Initialize Telegram client with configuration.

        Args:
            config_path: Path to configuration file containing API credentials
                        and allowed contacts list.

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required config fields are missing
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        # Initialize Pyrogram client
        self.app = Client(
            name="xiaozhi_telegram",
            api_id=self.config["api_id"],
            api_hash=self.config["api_hash"],
            phone_number=self.config["phone"],
        )
        
        self.allowed_contacts = set(self.config.get("allowed_contacts", []))
        logger.info(f"Initialized Telegram client with {len(self.allowed_contacts)} allowed contacts")

    def _load_config(self) -> dict:
        """Load and validate configuration file.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required fields are missing
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {self.config_path}\n"
                f"Please copy telegram_config.json.template to telegram_config.json "
                f"and fill in your credentials."
            )

        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        required_fields = ["api_id", "api_hash", "phone"]
        missing_fields = [field for field in required_fields if field not in config]
        
        if missing_fields:
            raise ValueError(f"Missing required fields in config: {missing_fields}")

        return config

    async def get_contacts(self) -> list[dict]:
        """Get all Telegram contacts.

        Returns:
            List of dictionaries with contact information:
            [
                {
                    "id": 123456789,
                    "first_name": "John",
                    "last_name": "Doe",
                    "full_name": "John Doe",
                    "username": "@johndoe",
                    "phone": "+1234567890"
                },
                ...
            ]

        Example:
            >>> client = TelegramClient()
            >>> async with client.app:
            ...     contacts = await client.get_contacts()
            ...     for contact in contacts:
            ...         print(f"{contact['full_name']} - {contact['username']}")
        """
        contacts_list = []

        async with self.app:
            # Get all dialogs (conversations)
            async for dialog in self.app.get_dialogs():
                chat = dialog.chat
                
                # Filter only users (not groups, channels, bots)
                if chat.type.value == "private" and not chat.is_bot:
                    contact_info = {
                        "id": chat.id,
                        "first_name": chat.first_name or "",
                        "last_name": chat.last_name or "",
                        "full_name": " ".join(
                            filter(None, [chat.first_name, chat.last_name])
                        ),
                        "username": f"@{chat.username}" if chat.username else "",
                        "phone": chat.phone_number or "",
                    }
                    contacts_list.append(contact_info)

        logger.info(f"Retrieved {len(contacts_list)} contacts")
        return contacts_list

    async def send_message(self, contact_name: str, message: str) -> dict:
        """Send message to a contact by name.

        Args:
            contact_name: Name of the contact (first name or full name)
            message: Text message to send

        Returns:
            Dictionary with send status:
            {
                "success": True/False,
                "message": "Status message",
                "contact": {...}  # Contact info if found
            }

        Raises:
            PermissionError: If contact is not in allowed list

        Example:
            >>> client = TelegramClient()
            >>> async with client.app:
            ...     result = await client.send_message("John Doe", "Hello!")
            ...     print(result["message"])
        """
        # Check if contact is allowed
        if contact_name not in self.allowed_contacts:
            error_msg = (
                f"Contact '{contact_name}' is not in allowed list. "
                f"Allowed contacts: {sorted(self.allowed_contacts)}"
            )
            logger.error(error_msg)
            raise PermissionError(error_msg)

        async with self.app:
            # Search for contact
            found_contact = None
            async for dialog in self.app.get_dialogs():
                chat = dialog.chat
                
                if chat.type.value == "private" and not chat.is_bot:
                    full_name = " ".join(
                        filter(None, [chat.first_name, chat.last_name])
                    )
                    
                    # Match by first name or full name
                    if (
                        contact_name.lower() == (chat.first_name or "").lower()
                        or contact_name.lower() == full_name.lower()
                    ):
                        found_contact = chat
                        break

            if not found_contact:
                error_msg = f"Contact '{contact_name}' not found in your Telegram contacts"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "contact": None,
                }

            # Send message
            try:
                await self.app.send_message(
                    chat_id=found_contact.id,
                    text=message
                )
                
                success_msg = f"Message sent to {contact_name}"
                logger.info(success_msg)
                
                return {
                    "success": True,
                    "message": success_msg,
                    "contact": {
                        "id": found_contact.id,
                        "name": " ".join(
                            filter(None, [found_contact.first_name, found_contact.last_name])
                        ),
                        "username": found_contact.username,
                    },
                }
            except Exception as e:
                error_msg = f"Failed to send message: {str(e)}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": error_msg,
                    "contact": None,
                }


# Convenience functions for direct usage
async def get_all_contacts(config_path: str = "telegram_config.json") -> list[dict]:
    """Get all Telegram contacts.

    Args:
        config_path: Path to configuration file

    Returns:
        List of contact dictionaries
    """
    client = TelegramClient(config_path)
    return await client.get_contacts()


async def send_telegram_message(
    contact_name: str,
    message: str,
    config_path: str = "telegram_config.json"
) -> dict:
    """Send message to a Telegram contact.

    Args:
        contact_name: Name of the contact
        message: Text message to send
        config_path: Path to configuration file

    Returns:
        Send status dictionary
    """
    client = TelegramClient(config_path)
    return await client.send_message(contact_name, message)
