# xiaozhi-mcp

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server providing a suite of AI-ready tools — weather, grocery lists, crypto/currency rates, calendars, fuel prices, Telegram messaging, and more. Supports **stdio**, **streamable-HTTP**, and **WebSocket-pipe** transports.

Managed by [uv](https://docs.astral.sh/uv/).

---

## Quickstart

```bash
uv sync
uv run python tools.py          # stdio (single server)
uv run python run_http.py       # HTTP on 0.0.0.0:8000
uv run python mcp_pipe.py       # stdio ↔ WebSocket pipe (Docker default)
```

## Tools

Tools are registered in `tools.py`. Tools that require credentials are **automatically disabled** when the relevant env var or config file is missing.

| Tool | Description | Requires |
|---|---|---|
| `calculator` | Evaluates Python math expressions (`math`/`random` available) | — |
| `weather` | Current weather by city (OpenWeatherMap) | `OPENWEATHER_API_KEY` |
| `weather_plan` | Multi-day forecast with outdoor score and clothing advice | `OPENWEATHER_API_KEY` |
| `get_currency_rates` | Official USD, EUR, Gold rates from the National Bank of Ukraine | — |
| `get_crypto_prices` | BTC, ETH, SOL spot prices in USD via CoinGecko | — |
| `get_okko_fuel_price_a95` | Current A-95 petrol price at OKKO stations (UAH) | — |
| `add_product` / `remove_product` / `list_products` | In-memory product list | — |
| `add_grocery_item` / `remove_grocery_item` / `list_grocery_items` / `complete_grocery_item` / `update_grocery_spec` | Bring! shopping list management | `BRING_EMAIL` + `BRING_PASSWORD` |
| `list_google_calendars` / `get_google_calendar_events` | Google Calendar read access | credentials at `~/.config/xiaozhi/credentials.json` |
| `list_outlook_calendars` / `get_outlook_calendar_events` | Microsoft Outlook / Teams calendar read access | `O365_CLIENT_ID` + `O365_CLIENT_SECRET` |

## Configuration

Copy `.env.example` to `.env` and fill in the values you need:

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `MCP_ENDPOINT` | WebSocket endpoint used by `mcp_pipe.py` (e.g. `ws://host:port/path`) |
| `OPENWEATHER_API_KEY` | [OpenWeatherMap](https://openweathermap.org/api) free-tier key |
| `TAVILY_API_KEY` | [Tavily](https://tavily.com/) search API key |
| `BRING_EMAIL` / `BRING_PASSWORD` | Bring! grocery app credentials |
| `O365_CLIENT_ID` / `O365_CLIENT_SECRET` | Azure app registration credentials for Outlook |
| `O365_TENANT_ID` | *(optional)* Azure tenant ID (default: `common`) |

## Transport Modes

### stdio (default, Claude Desktop / cursor)

```bash
uv run python tools.py
```

`mcp_config.json` example:
```json
{
  "mcpServers": {
    "xiaozhi": {
      "type": "stdio",
      "command": "python",
      "args": ["tools.py"]
    }
  }
}
```

### Streamable HTTP

```bash
MCP_HOST=0.0.0.0 MCP_PORT=8000 uv run python run_http.py
```

### WebSocket Pipe

Bridges local stdio MCP servers to a remote WebSocket endpoint (used in the Docker deployment):

```bash
MCP_ENDPOINT=ws://your-server:port/path uv run python mcp_pipe.py
```

## Docker

Two images are provided:

| Image | Entry point | Purpose |
|---|---|---|
| `Dockerfile` | `mcp_pipe.py` | WebSocket pipe — connects local servers to a remote WS endpoint |
| `Dockerfile.http` | `run_http.py` | HTTP transport — exposes MCP over `streamable-http` on port 8000 |

### Run with Docker Compose

```bash
cp .env.example .env   # fill in your values
docker compose up -d
```

- **`xiaozhi-mcp`** — WebSocket pipe service (reads `MCP_ENDPOINT` from `.env`)
- **`xiaozhi-mcp-http`** — HTTP service on port `8000`, mounts `~/.config/xiaozhi` for Google Calendar credentials

## Google Calendar Setup

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Google Calendar API**.
3. Create **OAuth 2.0 credentials** (Desktop app).
4. Download `credentials.json` and place it at:
   ```
   ~/.config/xiaozhi/credentials.json
   ```
5. On first run an OAuth flow will open in the browser and write `token.json` to the same folder.

## Outlook / Teams Calendar Setup

1. Register an app at [Azure Portal](https://portal.azure.com/) → Azure Active Directory → App registrations.
2. Add the `Calendars.Read` delegated permission under Microsoft Graph.
3. Set `O365_CLIENT_ID` and `O365_CLIENT_SECRET` in `.env`.

## Telegram Module Setup

The Telegram module lets you send messages from your own account to whitelisted contacts.

### 1. Get Telegram API Credentials

1. Go to https://my.telegram.org/apps and log in.
2. Click **"Create application"** and fill in the fields.
3. Copy your `api_id` and `api_hash`.

### 2. Configure

```bash
cp telegram_config.json.template telegram_config.json
```

```json
{
  "api_id": "12345678",
  "api_hash": "abcdef1234567890abcdef1234567890",
  "phone": "+1234567890",
  "allowed_contacts": []
}
```

### 3. Fetch Contacts

```python
import asyncio
from xiaozhi_mcp.telegram import get_all_contacts

async def main():
    contacts = await get_all_contacts()
    for c in contacts:
        print(f"{c['full_name']} - {c['username']}")

asyncio.run(main())
```

On first run you will be prompted for the Telegram verification code.

### 4. Add Allowed Contacts

Add exact names (as they appear in your contacts list) to `allowed_contacts` in `telegram_config.json`.

### Security Notes

- `telegram_config.json` and `*.session` files are in `.gitignore`.
- Only contacts listed in `allowed_contacts` can receive messages.

### Troubleshooting

- **"Contact not in allowed list"** — add the name to `allowed_contacts`.
- **"Contact not found"** — use the exact name from the contacts list.
- **Phone code prompt** — enter the code sent to your Telegram app.

## Development

```bash
uv sync --dev
uv run pytest
uv run ruff check .
uv run mypy .
```
