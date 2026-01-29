from dataclasses import dataclass, asdict
import json
import os
import time
from app.core.config import Config

@dataclass
class GiftLog:
    serial_no: int
    timestamp: str
    livestream_id: str
    gift_id: int
    gift_count: int
    account_name: str
    ip_address: str
    location: str

    def save(self):
        # Create dir if not exists
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        
        # Load existing for serial number check (simple approach) or plain append
        # For structured JSON array, we need to read/write entire file or use line-delimited JSON (NDJSON)
        # NDJSON is better for appending. Let's use NDJSON for log file.
        
        entry = asdict(self)
        
        with open(Config.ANALYTICS_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")
