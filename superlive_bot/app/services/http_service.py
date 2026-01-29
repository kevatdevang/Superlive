import httpx
from app.core.logger import logger

class AsyncHTTPClient:
    def __init__(self, headers=None, base_url=None, proxy=None):
        self.client = httpx.AsyncClient(
            headers=headers, 
            base_url=base_url or "", 
            timeout=30.0, 
            follow_redirects=True,
            http2=True,
            proxy=proxy
        )

    async def get(self, url, params=None, **kwargs):
        try:
            resp = await self.client.get(url, params=params, **kwargs)
            return resp
        except Exception as e:
            logger.error(f"HTTP GET Error [{url}]: {type(e).__name__} - {e}")
            return None

    async def post(self, url, json=None, data=None, **kwargs):
        try:
            resp = await self.client.post(url, json=json, data=data, **kwargs)
            return resp
        except Exception as e:
            logger.error(f"HTTP POST Error [{url}]: {type(e).__name__} - {e}")
            return None

    async def delete(self, url, **kwargs):
        try:
            resp = await self.client.delete(url, **kwargs)
            return resp
        except Exception as e:
            logger.error(f"HTTP DELETE Error [{url}]: {type(e).__name__} - {e}")
            return None

    async def close(self):
        await self.client.aclose()
