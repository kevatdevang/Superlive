import certifi
import logging
import time
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import config

logger = logging.getLogger("superlive.core.mongo")

class MongoDBService:
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self.enabled = False
        
        # Access URI via config
        uri = getattr(config, "MONGO_URI", None)
        
        if uri and "<db_password>" not in uri:
             try:
                # Motor client creation is non-blocking
                self.client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000, tlsCAFile=certifi.where())
                self.db = self.client.get_database("Superlive")
                self.collection = self.db.get_collection("accounts")
                self.enabled = True
             except Exception as e:
                logger.error(f"❌ MongoDB Init Failed: {e}")
                self.enabled = False
        else:
            logger.warning("⚠️ MongoDB URI missing or contains placeholder. MongoDB logging disabled.")

    async def insert_email(self, email):
        if not self.enabled or self.collection is None: return
        try:
            doc = {
                "email": email,
                "timestamp": int(time.time()),
                "status": "created_with_balance"
            }
            await self.collection.insert_one(doc)
            # logger.info(f"💾 Saved to Mongo: {email}") 
        except Exception as e:
            logger.error(f"⚠️ Mongo Save Error: {e}")

mongo_service = MongoDBService()
