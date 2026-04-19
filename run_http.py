import os
import asyncio
from tools import mcp, list_tools_on_startup

host = os.getenv('MCP_HOST', '0.0.0.0')
port = int(os.getenv('MCP_PORT', '8000'))

if __name__ == '__main__':
    asyncio.run(list_tools_on_startup())
    mcp.run(transport='streamable-http', host=host, port=port)
