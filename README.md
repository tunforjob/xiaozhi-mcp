# xiaozhi-mcp

Minimal Python project managed by uv.

## Run

```bash
uv venv
source .venv/bin/activate
uv sync
uv run python -m xiaozhi_mcp
```

## Telegram Module Setup

The Telegram module allows you to send messages from your account to selected contacts.

### 1. Get Telegram API Credentials

1. Go to https://my.telegram.org/apps
2. Log in with your phone number
3. Click "Create application"
4. Fill in the required fields:
   - App title: `xiaozhi-mcp`
   - Short name: `xiaozhi`
   - Platform: Choose any (e.g., Desktop)
5. Copy your `api_id` and `api_hash`

### 2. Configure Telegram Module

```bash
# Copy the template
cp telegram_config.json.template telegram_config.json

# Edit the config file
nano telegram_config.json
```

Fill in your credentials:
```json
{
  "api_id": "12345678",
  "api_hash": "abcdef1234567890abcdef1234567890",
  "phone": "+1234567890",
  "allowed_contacts": []
}
```

### 3. Get Your Contacts List

First, you need to get your contacts to select who can receive messages:

```python
import asyncio
from xiaozhi_mcp.telegram import get_all_contacts

async def main():
    contacts = await get_all_contacts()
    for contact in contacts:
        print(f"{contact['full_name']} - {contact['username']}")

asyncio.run(main())
```

On first run, you'll be prompted to enter the verification code sent to your Telegram app.

### 4. Add Allowed Contacts

Edit `telegram_config.json` and add contact names to the `allowed_contacts` list:

```json
{
  "api_id": "12345678",
  "api_hash": "abcdef1234567890abcdef1234567890",
  "phone": "+1234567890",
  "allowed_contacts": [
    "John Doe",
    "Jane Smith"
  ]
}
```

**Important**: Use exact names as they appear in your contacts list.

### 5. Send Messages

```python
import asyncio
from xiaozhi_mcp.telegram import send_telegram_message

async def main():
    result = await send_telegram_message(
        contact_name="John Doe",
        message="Hello from xiaozhi-mcp!"
    )
    print(result["message"])

asyncio.run(main())
```

### Security Notes

- `telegram_config.json` is in `.gitignore` - your credentials won't be committed
- `*.session` files are also ignored - these contain your login session
- Only contacts in `allowed_contacts` can receive messages
- Session files allow you to stay logged in between runs

### Troubleshooting

**"Contact not in allowed list"**: Add the contact name to `allowed_contacts` in your config

**"Contact not found"**: Make sure you're using the exact name from the contacts list

**Phone code prompt**: On first run, enter the code sent to your Telegram app
