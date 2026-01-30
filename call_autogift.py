import httpx
import asyncio

URL = "http://127.0.0.1:5000/auto/gift"
PAYLOAD = {
    "code": 10,
    "livestream_id": [131667356],
    "worker": 4,
    "use_proxy": False,
    "base": 1,
    "use_vpn": True
}

async def call_endpoint():
    print(f"Sending POST to {URL} with payload: {PAYLOAD}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(URL, json=PAYLOAD, timeout=10.0)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
    except httpx.ConnectError:
        print("Error: Could not connect to the server. Is it running on port 5000?")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(call_endpoint())
