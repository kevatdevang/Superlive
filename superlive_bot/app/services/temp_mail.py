import asyncio
import time
from app.services.http_service import AsyncHTTPClient
from app.core.config import Config
from app.core.logger import logger

class TempMailService:
    def __init__(self):
        self.headers = {
            'authority': 'tempmail.so',
            'accept': 'application/json, text/plain, */*',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        self.http = AsyncHTTPClient(headers=self.headers, base_url=Config.TEMP_MAIL_URL)

    async def get_email(self):
        """
        Fetches a new temporary email.
        """
        try:
            # Init session cookies
            await self.http.get("/") 
            
            timestamp = int(time.time() * 1000)
            url = f"/us/api/inbox?requestTime={timestamp}&lang=us"
            
            resp = await self.http.get(url)
            if resp and resp.status_code == 200:
                data = resp.json()
                if 'data' in data and 'name' in data['data']:
                    email = data['data']['name']
                    logger.info(f"📧 Acquired Email: {email}")
                    return email
            
            logger.error("Failed to acquire email from API.")
            return None
        except Exception as e:
            logger.error(f"TempMail Error: {e}")
            return None

    async def get_verification_code(self, email, retries=25):
        """
        Polls for verification code (6 digits).
        """
        logger.info(f"⏳ Polling inbox for code...") # Simple log
        
        import re
        
        for i in range(retries):
            await asyncio.sleep(3)
            try:
                timestamp = int(time.time() * 1000)
                url = f"/us/api/inbox?requestTime={timestamp}&lang=us"
                
                resp = await self.http.get(url)
                if resp and resp.status_code == 200:
                    data = resp.json()
                    if 'data' in data and 'inbox' in data['data']:
                        inbox = data['data']['inbox']
                        if len(inbox) > 0:
                            # Parse code from latest message
                            text_body = inbox[0].get('textBody', '')
                            match = re.search(r'\b(\d{6})\b', text_body)
                            if match:
                                code = match.group(1)
                                logger.info(f"📬 Received Code: {code}")
                                return code
            except Exception as e:
                logger.debug(f"Polling error: {e}")
                
        logger.error("❌ Verification code timeout.")
        return None

    async def delete_inbox(self):
        """
        Deletes the current inbox/email.
        """
        try:
            timestamp = int(time.time() * 1000)
            url = f"/us/api/inbox?requestTime={timestamp}&lang=us"
            
            resp = await self.http.delete(url)
            if resp and resp.status_code == 200:
                logger.info("🗑️  Inbox Deleted.")
                return True
            return False
        except Exception as e:
            logger.error(f"TempMail Delete Error: {e}")
            return False

    async def close(self):
        await self.http.close()
