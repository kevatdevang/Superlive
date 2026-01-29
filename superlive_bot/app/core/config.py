import os

class Config:
    BASE_URL = "https://api.spl-web.link"
    TEMP_MAIL_URL = "https://tempmail.so"
    
    # Files
    # Determine project root relative to this file (app/core/config.py)
    # config.py -> core -> app -> superlive_bot (ROOT)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    
    ANALYTICS_FILE = os.path.join(DATA_DIR, 'gift_analytics.json')
    ACCOUNT_FILE = os.path.join(DATA_DIR, 'accounts.txt')
    PROXY_FILE = os.path.join(DATA_DIR, "superlive_proxies.txt")

    # Headers
    DEFAULT_HEADERS = {
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "origin": "https://superlive.chat",
        "referer": "https://superlive.chat/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
