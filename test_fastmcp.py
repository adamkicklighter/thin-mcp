import httpx
import asyncio

async def test_connection():
    async with httpx.AsyncClient() as client:
        # Try to hit the SSE endpoint
        print("Connecting to SSE...")
        async with client.stream("GET", "http://127.0.0.1:8000/sse") as response:
            print(f"Status: {response.status_code}")
            print(f"Headers: {response.headers}")
            
            # Read first few lines
            count = 0
            async for line in response.aiter_lines():
                print(f"Line {count}: {repr(line)}")
                count += 1
                if count > 10:
                    break

if __name__ == "__main__":
    asyncio.run(test_connection())