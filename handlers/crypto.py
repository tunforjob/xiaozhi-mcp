from typing import Any, Dict

import httpx

API_URL = "https://api.coingecko.com/api/v3/simple/price"


def get_crypto_prices() -> Dict[str, Any]:
    """Get current Bitcoin, Ethereum, and Solana prices in USD from CoinGecko."""
    crypto_ids = "bitcoin,ethereum,solana"
    vs_currency = "usd"

    try:
        with httpx.Client() as client:
            response = client.get(
                API_URL,
                params={"ids": crypto_ids, "vs_currencies": vs_currency}
            )
            response.raise_for_status()
            data = response.json()

        return {
            "success": True,
            "prices": {
                "bitcoin": data.get("bitcoin", {}).get("usd"),
                "ethereum": data.get("ethereum", {}).get("usd"),
                "solana": data.get("solana", {}).get("usd")
            }
        }

    except httpx.HTTPStatusError as e:
        return {"success": False, "error": f"HTTP error (Status {e.response.status_code}): {e}"}
    except httpx.RequestError as e:
        return {"success": False, "error": f"Request error (Network/DNS): {e}"}
