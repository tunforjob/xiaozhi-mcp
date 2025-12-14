"""
Internet search module using Tavily API.
"""

import os
import asyncio
from typing import Any, Dict, List, Optional

from tavily import AsyncTavilyClient


class SearchService:
    """
    Service for performing internet searches using Tavily.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize the SearchService.

        Args:
            api_key: Tavily API key. If not provided, it will be read from TAVILY_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY is not set")
        self.client = AsyncTavilyClient(api_key=self.api_key)

    async def search(self, query: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Perform a search query.

        Args:
            query: The search query.
            **kwargs: Additional arguments to pass to the Tavily API
                     (e.g. search_depth="advanced", include_domains=[], etc.)

        Returns:
            The search results from Tavily API.
        """
        return await self.client.search(query, **kwargs)

    async def get_search_context(self, query: str, **kwargs: Any) -> str:
        """
        Get a context string based on the search query.
        Useful for RAG applications.
        """
        return await self.client.get_search_context(query, **kwargs)

    async def qna_search(self, query: str, **kwargs: Any) -> str:
        """
        Perform a Q&A search where the answer is directly returned.
        """
        return await self.client.qna_search(query, **kwargs)


if __name__ == "__main__":
    async def main() -> None:
        # Example usage
        try:
            service = SearchService()
            query = "What is the current weather in Tokyo?"
            print(f"Searching for: {query}")
            
            # Basic search
            results = await service.search(query, search_depth="basic")
            print("\nSearch Results:")
            for result in results.get("results", [])[:2]:
                print(f"- {result['title']}: {result['url']}")

            # Q&A Search
            print("\nQ&A Search:")
            answer = await service.qna_search(query)
            print(f"Answer: {answer}")

        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(main())
