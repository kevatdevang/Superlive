
# Setup logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrator")

import re
import os
import sys
import asyncio
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.mongo import mongo_service
from app.core.config import config

async def migrate():
    log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "superlive.log")
    
    if not os.path.exists(log_file):
        logger.error(f"Log file not found: {log_file}")
        return

    logger.info(f"Reading {log_file}...")
    
    count = 0
    skipped = 0
    
    # Regex to find: 2026-01-21 12:02:18 ... Signup Success (email)
    pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) .*Signup Success \((.*)\)")
    
    if not mongo_service.enabled:
        logger.error("MongoDB not enabled! Check config.")
        return
        
    # Verify connection
    try:
        print("[INFO] Pinging MongoDB...")
        await mongo_service.client.admin.command('ping')
        print("[INFO] MongoDB Connected!")
    except Exception as e:
        print(f"[ERROR] Ping Failed: {e}")
        logger.error(f"MongoDB Connection Failed: {e}")
        return

    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                dt_str = match.group(1)
                email = match.group(2)
                
                try:
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                    timestamp = int(dt.timestamp())
                    
                    doc = {
                        "email": email,
                        "timestamp": timestamp,
                        "status": "created_with_balance"
                    }
                    
                    # Check if exists
                    existing = await mongo_service.collection.find_one({"email": email})
                    if existing:
                        skipped += 1
                        continue
                        
                    await mongo_service.collection.insert_one(doc)
                    count += 1
                    if count % 10 == 0:
                        print(f"Migrated {count}...", end="\r")
                        
                except Exception as e:
                    logger.error(f"Error processing line: {line.strip()} - {e}")
                    
    logger.info(f"Migration Complete. Imported: {count}, Skipped: {skipped}")

if __name__ == "__main__":
    asyncio.run(migrate())
