import asyncio
import uuid
import random
import string
import time
from app.services.http_service import AsyncHTTPClient
from app.core.config import Config
from app.core.logger import logger
from app.core.exceptions import SignupLimitError

class SuperliveService:
    def __init__(self, proxy=None):
        self.headers = Config.DEFAULT_HEADERS.copy()
        self.proxy = proxy
        self.http = AsyncHTTPClient(headers=self.headers, base_url=Config.BASE_URL, proxy=self.proxy)
        self.client_params = {}
        self.device_id = None
        self.verification_id = None
        self.token = None

    def _generate_uuid(self):
        return str(uuid.uuid4())
        
    def _generate_installation_id(self):
        return str(uuid.uuid4())

    def _generate_random_string(self, length=32):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    async def register_device(self):
        url = "/api/web/device/register"
        self.client_params = {
            "os_type": "web",
            "app_build": "4.1.16",
            "app": "superlive",
            "build_code": "806-2949349-prod",
            "app_language": "en",
            "device_language": "en",
            "device_preferred_languages": ["en-US"],
            "source_url": "https://superlive.chat/",
            "session_source_url": "https://superlive.chat/",
            "adjust_web_uuid": self._generate_uuid(),
            "incognito": True,
            "installation_id": self._generate_installation_id(),
            "uuid_c1": self._generate_random_string(32),
            "web_type": 1
        }
        
        # Reset headers for new device
        self.headers = Config.DEFAULT_HEADERS.copy()
        
        payload = {"client_params": self.client_params}
        
        resp = await self.http.post(url, json=payload)
        if resp and resp.status_code == 200:
            data = resp.json()
            if 'guid' in data:
                self.device_id = data['guid']
            else:
                 self.device_id = uuid.uuid4().hex
            
            # Update Headers
            self.headers['device-id'] = self.device_id
            # Re-init client with new headers
            await self.http.close() 
            self.http = AsyncHTTPClient(headers=self.headers, base_url=Config.BASE_URL, proxy=self.proxy)
            
            logger.info(f"📱 Device Registered: {self.device_id[:8]}...")
            return True
            
        if resp:
            logger.error(f"Device Register Failed: {resp.text}")
        return False

    async def send_verification_code(self, email):
        url = "/api/web/signup/send_email_verification_code"
        payload = {
            "client_params": self.client_params,
            "email": email,
            "force_new": False
        }
        resp = await self.http.post(url, json=payload)
        if resp and resp.status_code == 200:
            data = resp.json()
            # Try to fetch ID
            if 'data' in data and 'email_verification_id' in data['data']:
                self.verification_id = data['data']['email_verification_id']
            elif 'email_verification_id' in data:
                self.verification_id = data['email_verification_id']
            
            if self.verification_id:
                logger.info(f"📨 Verification Code Sent. ID: {self.verification_id}")
                return True
        
        if resp:
            logger.error(f"Send Code Failed: {resp.text}")
            try:
                err_data = resp.json()
                if 'error' in err_data and err_data['error'].get('code') == 12:
                    raise SignupLimitError("Signup limit reached (Send Code).")
            except SignupLimitError:
                raise
            except:
                pass
        return False

    async def verify_email(self, code):
        url = "/api/web/signup/verify_email"
        payload = {
            "client_params": self.client_params,
            "email_verification_id": self.verification_id,
            "code": int(code)
        }
        resp = await self.http.post(url, json=payload)
        if resp and resp.status_code == 200:
            logger.info("✅ Email Verified.")
            return True
            
        if resp:
            logger.error(f"Verify Email Failed: {resp.text}")
        return False

    async def complete_signup(self, email):
        url = "/api/web/signup/email"
        payload = {
            "client_params": self.client_params,
            "email": email,
            "password": email # Using email as password
        }
        resp = await self.http.post(url, json=payload)
        if resp and resp.status_code == 200:
            data = resp.json()
            token = None
            if 'data' in data and 'token' in data['data']:
                token = data['data']['token']
            elif 'token' in data:
                token = data['token']
            
            if token:
                self.token = token
                self.headers['authorization'] = f"Token {self.token}"
                # Update client with auth header
                await self.http.close()
                self.http = AsyncHTTPClient(headers=self.headers, base_url=Config.BASE_URL)
                logger.info("🎉 Account Created & Logged In!")
                return True
        
        # Check for error msg
        if resp:
            logger.error(f"Signup Failed: {resp.text}")
            try:
                err_data = resp.json()
                if 'error' in err_data and err_data['error'].get('code') == 12:
                    raise SignupLimitError("Signup limit reached.")
            except SignupLimitError:
                raise
            except:
                pass
        return False

    async def update_profile(self):
        url = "/api/web/users/update"
        
        names = ["Piyush"]
        emojis = ["🧡", "💛", "💚", "💙", "💜", "🤎", "🖤", "🤍", "💖"]
        random_name = f"{random.choice(names)} {random.choice(emojis)}"
        
        payload = {
            "client_params": self.client_params,
            "name": random_name,
            "gender": 1,
            "birthday": 1115538908000
        }
        
        resp = await self.http.post(url, json=payload)
        if resp and resp.status_code == 200:
            logger.info(f"✏️  Profile Updated: {random_name}")
            return random_name
        return None

    async def set_country_preferences(self):
        url = "/api/web/discover/user_countries"
        payload = {
            "client_params": self.client_params,
            "discover_countries": ["IN", "NP"]
        }
        
        resp = await self.http.post(url, json=payload)
        if resp and resp.status_code == 200:
            logger.info("🌍 Country Preferences Set: IN, NP")
            return True
        return False

    async def discover_streams(self):
        url = "/api/web/discover"
        payload = {
            "client_params": self.client_params,
            "next": None,
            "type": 0
        }
        resp = await self.http.post(url, json=payload)
        streams = []
        if resp and resp.status_code == 200:
            data = resp.json()
            if 'items' in data:
                for item in data['items']:
                    info = {}
                    if 'stream_details' in item:
                        info['id'] = item['stream_details'].get('livestream_id')
                    if 'user' in item:
                        info['user_id'] = item['user'].get('user_id')
                    
                    if info.get('id'):
                        streams.append(info)
            logger.info(f"🔎 Discovered {len(streams)} streams.")
        return streams

    async def send_gift(self, livestream_id, gift_id=5141):
        url = "/api/web/livestream/chat/send_gift"
        payload = {
            "client_params": self.client_params,
            "gift_context": 1,
            "livestream_id": int(livestream_id),
            "gift_id": int(gift_id),
            "guids": [str(uuid.uuid4())],
            "gift_batch_size": 1
        }
        resp = await self.http.post(url, json=payload)
        if resp and resp.status_code == 200:
            data = resp.json()
            if data.get('success'):
                logger.info(f"🎁 Gift Sent to {livestream_id}")
                return True
            else:
                logger.warning(f"Gift Failed: {data.get('error', {}).get('message')}")
        return False

    async def logout(self):
        url = "/api/web/user/logout"
        payload = {"client_params": self.client_params}
        
        try:
            resp = await self.http.post(url, json=payload)
            if resp and resp.status_code == 200:
                logger.info("👋 Logged Out.")
                return True
        except:
            pass
        return False

    async def close(self):
        await self.http.close()
