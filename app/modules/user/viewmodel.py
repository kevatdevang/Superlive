import logging
import httpx
import uuid
from app.core.client import SuperliveClient
from app.core.config import config
from app.modules.api.viewmodel import SuperliveError

logger = logging.getLogger("superlive.modules.user.viewmodel")

class UserViewModel:
    
    async def _make_request(self, method: str, endpoint: str, client, error_context: str = "Request failed", base_url: str = None, **kwargs):
        """
        Helper method to make requests with fallback to backup URL on network errors or specific status codes.
        (Duplicated from ApiViewModel to ensure module independence)
        """
        if base_url:
            if base_url.endswith("/") and endpoint.startswith("/"):
                url = f"{base_url[:-1]}{endpoint}"
            elif not base_url.endswith("/") and not endpoint.startswith("/"):
                url = f"{base_url}/{endpoint}"
            else:
                url = f"{base_url}{endpoint}"
            
            urls = [url]
        else:
            urls = [
                f"{config.API_BASE_URL}{endpoint}",
                f"{config.API_BASE_URL_BACKUP}{endpoint}"
            ]
        
        last_exception = None
        
        for i, url in enumerate(urls):
            is_backup = i > 0
            try:
                if is_backup:
                    logger.warning(f"Retrying with backup URL: {url}")
                    
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code in [403, 502, 503, 504] and not is_backup:
                    logger.warning(f"Primary URL failed with status {e.response.status_code}. Attempting backup.")
                    last_exception = e
                    continue
                
                logger.error(f"{error_context}: {e.response.text}")
                try:
                    details = e.response.json()
                except:
                    details = {"error": e.response.text}
                raise SuperliveError(error_context, e.response.status_code, details)
                
            except (httpx.NetworkError, httpx.TimeoutException) as e:
                if not is_backup:
                    logger.warning(f"Network error on primary URL: {e}. Attempting backup.")
                    last_exception = e
                    continue
                
                logger.error(f"Unexpected {error_context.lower()} error: {e}")
                raise SuperliveError(f"Unexpected error: {str(e)}")
                
            except Exception as e:
                logger.error(f"Unexpected {error_context.lower()} error: {e}")
                raise SuperliveError(f"Unexpected error: {str(e)}")
                
        raise SuperliveError(f"Unexpected error: {str(last_exception)}")

    def _get_client_params(self, user_id=None):
        source_url = "https://superlive.chat/"
        if user_id:
            source_url = f"https://superlive.chat/profile/{user_id}?isFromSearch=true"
            
        return {
            "os_type": "web",
            "ad_nationality": None,
            "app_build": "3.22.9",
            "app": "superlive",
            "build_code": "713-2944998-prod",
            "app_language": "en",
            "device_language": "en",
            "device_preferred_languages": ["en-US"],
            "source_url": source_url,
            "session_source_url": "https://superlive.chat/",
            "referrer": "https://superlive.chat/",
            "adid": "b6cc4d375333e71764c7cab155c28e29", # Updated based on payload
            "adjust_attribution_data": {
                "adid": "b6cc4d375333e71764c7cab155c28e29",
                "tracker_token": "mii5ej6",
                "tracker_name": "Organic",
                "network": "Organic"
            },
            "adjust_web_uuid": str(uuid.uuid4()),
            "firebase_analytics_id": "673275269.1767002946",
            "incognito": True,
            "installation_id": str(uuid.uuid4()),
            "rtc_id": "2026725372",
            "uuid_c1": "hy9UEJBAKJnGxLJ_2aVnh6w0EJMGE6XD",
            "vl_cid": None,
            "ttp": "01KDMSAF4EXX064QRCCBAWSEHG_.tt.1",
            "twclid": None,
            "tdcid": None,
            "fbc": None,
            "fbp": "fb.1.1767002947091.638581389143503461",
            "ga_session_id": "1767002945",
            "web_type": 1
        }

    async def get_other_user_profile(self, user_id, token=None, client=None, base_url=None):
        if client is None:
            client = SuperliveClient.get_client()
            
        headers = client.headers.copy()
        if token:
            headers["authorization"] = f"Token {token}"
        
        payload = {
            "client_params": self._get_client_params(user_id),
            "user_id": str(user_id),
            "is_from_search": True
        }
        
        return await self._make_request(
            "POST", 
            "/users/profile", 
            client, 
            headers=headers, 
            json=payload, 
            error_context="Get other user profile failed",
            base_url=base_url
        )

user_viewmodel = UserViewModel()