import asyncio
import time
import random
import os
from datetime import datetime

from app.services.superlive import SuperliveService
from app.services.temp_mail import TempMailService
from app.core.logger import logger
from app.models.log_entry import GiftLog
from app.core.config import Config
from app.core.exceptions import SignupLimitError

class GiftBotViewModel:
    def __init__(self):
        # We instantiate services per worker ideally, but for now sharing is okay if they are stateless enough.
        # However, SuperliveService holds state (token, device_id).
        # So we should instantiate services INSIDE the worker loop.
        self.workers = []
        self.pause_event = asyncio.Event()
        self.stop_event = asyncio.Event()
        self.pause_event.set() # Default to running (unpaused) if started
        self.active_target_id = None

    async def start_workers(self, target_id, worker_count, use_proxy=0):
        """
        Starts concurrent tasks.
        use_proxy: If > 0, overrides worker_count (batch size).
        """
        # clear any previous stop signals
        self.stop_event.clear()
        self.pause_event.set()
        self.active_target_id = target_id
        
        # Load Proxies
        self.proxies = self._load_proxies()
        self.batch_offset = 0
        
        # Determine effective worker count
        self.proxy_enabled = False
        if use_proxy > 0:
            self.proxy_enabled = True
            if use_proxy > len(self.proxies):
                logger.warning(f"Requested {use_proxy} proxies but only have {len(self.proxies)}. Using max.")
                worker_count = len(self.proxies)
            else:
                worker_count = use_proxy
        else:
             logger.info(f"🚫 Proxy Mode: OFF (Direct Connection). Using {worker_count} workers.")
        
        self.active_worker_count = worker_count
        
        if worker_count < 1:
            logger.error("❌ No workers to start! Check proxy file or worker count.")
            return

        self.barrier = asyncio.Barrier(worker_count)
        
        logger.info(f"🚀 Starting {worker_count} Workers for Target: {target_id} | Proxies Available: {len(self.proxies)} | Proxy Enabled: {self.proxy_enabled}")
        
        for i in range(worker_count):
            # Create a task for each worker
            # Worker ID 0-indexed for array math, but logged as 1-indexed
            task = asyncio.create_task(self._worker_loop(i, target_id)) 
            self.workers.append(task)
            await asyncio.sleep(0.1) # Tiny stagger

    def _load_proxies(self):
        try:
            path = Config.PROXY_FILE
            if os.path.exists(path):
                with open(path, 'r') as f:
                    proxies = [line.strip() for line in f if line.strip()]
                return proxies
            else:
                logger.warning(f"Proxy file not found at: {path}")
        except Exception as e:
            logger.error(f"Error loading proxies: {e}")
        return []

    def _format_proxy(self, raw_proxy):
        # raw: ip:port:user:pass
        # target: http://user:pass@ip:port
        try:
            parts = raw_proxy.split(':')
            if len(parts) == 4:
                return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
            elif len(parts) == 2:
                return f"http://{parts[0]}:{parts[1]}"
        except:
            pass
        return None

    # ... pause/resume/stop methods unchanged ...

    async def _worker_loop(self, worker_idx, target_id):
        worker_id = worker_idx + 1
        logger.info(f"🤖 Worker #{worker_id} Started.")
        
        while not self.stop_event.is_set():
            # Check Pause
            await self.pause_event.wait()
            if self.stop_event.is_set(): break

            # Select Proxy
            proxy = None
            if self.proxies and self.proxy_enabled:
                proxy_idx = (self.batch_offset + worker_idx) % len(self.proxies)
                raw_proxy = self.proxies[proxy_idx]
                proxy = self._format_proxy(raw_proxy)
                # logger.info(f"Worker #{worker_id} using proxy {proxy_idx}: {raw_proxy}")

            # Instantiate services
            mail_service = TempMailService()
            superlive = SuperliveService(proxy=proxy)

            success = False
            try:
                logger.info(f"⚡ Worker #{worker_id}: Starting New Account Cycle...")
                
                # Run Cycle
                success = await self._run_single_cycle(worker_id, target_id, mail_service, superlive)
                
            except SignupLimitError:
                logger.warning(f"⚠️ Worker #{worker_id}: Signup Limit on Proxy! Rotating Batch...")
                # Rotate Batch: Shift offset by worker count (Next 5)
                # Simple check to avoid double-rotation if multiple hit at once
                if self.batch_offset % len(self.proxies) == (proxy_idx - worker_idx) % len(self.proxies):
                     self.batch_offset += self.active_worker_count
                
            except Exception as e:
                logger.error(f"Worker #{worker_id} Error: {e}")
            
            finally:
                # Cleanup
                if superlive: await superlive.logout(); await superlive.close()
                if mail_service: await mail_service.delete_inbox(); await mail_service.close()

            # Sync Barrier (Wait for others)
            try:
                if not self.stop_event.is_set():
                    # logger.info(f"Worker #{worker_id} Waiting for sync...")
                    await self.barrier.wait()
            except Exception as e:
                 if not self.stop_event.is_set():
                     logger.error(f"Barrier Error: {e}")

            # Delay
            if not self.stop_event.is_set():
                if success:
                    logger.info(f"⏳ Worker #{worker_id}: Cycle Complete. Waiting 5s...")
                else:
                    logger.warning(f"⚠️ Worker #{worker_id}: Cycle Failed. Retrying in 5s...")
                await asyncio.sleep(5) 

    async def _run_single_cycle(self, worker_id, target_id, mail_service, superlive):
        """
        The logic for a single account creation and gifting flow.
        Returns True if successful, False if failed early.
        """
        # 1. Register Device (Geo Removed)
        if not await superlive.register_device():
            return False

        # 2. Get Email
        email = await mail_service.get_email()
        if not email:
            return False

        # 3. Send Code
        if not await superlive.send_verification_code(email):
            return False

        # 4. Get Code
        code = await mail_service.get_verification_code(email)
        if not code:
            return False

        # 5. Verify Code
        if not await superlive.verify_email(code):
            return False

        # 6. Complete Signup
        if not await superlive.complete_signup(email):
            return False
            
        # Save Account
        with open(Config.ACCOUNT_FILE, "a") as f:
            f.write(f"{email}\n")

        # 7. Update Profile
        name = await superlive.update_profile()
        if not name:
            name = "Unknown"

        # 8. Set Preferences & Discover
        await superlive.set_country_preferences()
        streams = await superlive.discover_streams()
        if not streams:
            logger.warning(f"Worker #{worker_id}: No streams found.")
            return False

        # Target Logic
        sent_count = 0
        for i in range(4):
            if await superlive.send_gift(target_id):
                sent_count += 1
                await asyncio.sleep(0.5) # faster for worker
        
        # Log Logic for Target
        self._log_analytics(target_id, 5141, sent_count, name)

        # Random Logic
        other_streams = [s for s in streams if str(s['id']) != str(target_id)]
        random.shuffle(other_streams)
        selected = other_streams[:10]
        
        for s in selected:
            lid = s['id']
            if await superlive.send_gift(lid):
                self._log_analytics(lid, 5141, 1, name)
            await asyncio.sleep(0.5)
            
        return True

    def _log_analytics(self, livestream_id, gift_id, count, name):
        # Determine Serial No (count lines in file)
        try:
            with open(Config.ANALYTICS_FILE, 'r') as f:
                serial = sum(1 for _ in f) + 1
        except FileNotFoundError:
            serial = 1
            
        log = GiftLog(
            serial_no=serial,
            timestamp=datetime.now().isoformat(),
            livestream_id=str(livestream_id),
            gift_id=gift_id,
            gift_count=count,
            account_name=name,
            ip_address="Hidden",
            location="Hidden"
        )
        log.save()

    async def cleanup(self):
        await self.stop_workers()
