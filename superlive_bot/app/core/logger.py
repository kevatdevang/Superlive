import logging
import sys
from colorama import Fore, Style, init

# Initialize Colorama
init(autoreset=True)

class EmojiFormatter(logging.Formatter):
    """Custom formatter with tech-savvy emojis"""
    
    FORMATS = {
        logging.DEBUG:    Fore.CYAN + "🐛 [DEBUG] " + Style.RESET_ALL + "%(message)s",
        logging.INFO:     Fore.GREEN + "✨ [INFO]  " + Style.RESET_ALL + "%(message)s",
        logging.WARNING:  Fore.YELLOW + "⚠️ [WARN]  " + Style.RESET_ALL + "%(message)s",
        logging.ERROR:    Fore.RED + "❌ [ERROR] " + Style.RESET_ALL + "%(message)s",
        logging.CRITICAL: Fore.RED + Style.BRIGHT + "🔥 [CRIT]  " + Style.RESET_ALL + "%(message)s",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)

def setup_logger(name="SuperliveBot"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(EmojiFormatter())
    
    if not logger.handlers:
        logger.addHandler(ch)
        
        # File Handler (Added per user request)
        try:
            from logging.handlers import RotatingFileHandler
            import os
            
            # Ensure data dir exists (though Config might not be imported here to avoid circular, let's assume relative or re-import)
            log_dir = os.path.join(os.getcwd(), 'data')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'superlive.log')
            
            fh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8')
            fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            logger.addHandler(fh)
        except Exception as e:
            print(f"Failed to setup file logging: {e}")
        
    return logger

logger = setup_logger()
