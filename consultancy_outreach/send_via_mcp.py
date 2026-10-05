import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="cmd.exe",
        args=["/c", "npx", "-y", "@gongrzhe/server-gmail-autoauth-mcp"]
    )
    
    with open('email_payloads.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Sending {len(data)} emails via MCP...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            for i, item in enumerate(data):
                try:
                    result = await session.call_tool("send_email", arguments=item)
                    print(f"[{i+1}/{len(data)}] Sent to {item['to'][0]} - Result: {result}")
                except Exception as e:
                    print(f"[{i+1}/{len(data)}] Failed for {item['to'][0]} - Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
