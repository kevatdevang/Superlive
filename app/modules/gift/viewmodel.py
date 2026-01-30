import logging
import asyncio
import random
import time
import httpx
from fake_useragent import UserAgent
from app.core.config import config
from app.modules.api.viewmodel import api_viewmodel, SuperliveError
from app.modules.tempmail.viewmodel import temp_mail_viewmodel
from app.core.device import register_device
from app.core.mongo import mongo_service

logger = logging.getLogger("superlive.modules.gift.viewmodel")

class GiftViewModel:
    def __init__(self):
        self.is_active = False
        self.current_task = None
        self.ua = UserAgent()

    async def process_single_account(self, livestream_id, worker_index, proxy, superlive_base=1, name=None, use_vpn=False):
        """
        Executes a single account lifecycle: Register -> Verify -> Update Profile -> Send 4 Gifts -> Logout.
        Returns when finished.
        """
        attempt_id = f"{worker_index}-{int(time.time())}"
        worker_display_id = worker_index + 1
        
        # Resolve Base URL
        base_url = config.API_BASES.get(superlive_base, config.API_BASE_URL)
        logger.info(f"➡️ [Worker {worker_display_id}] Starting cycle with Base URL: {base_url}")
        
        # Random Domain
        domain_config = random.choice(config.DOMAINS)
        
        # Random User Agent
        random_ua = self.ua.random
        
        headers = {
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": domain_config["origin"],
            "priority": "u=1, i",
            "referer": domain_config["referer"],
            "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": random_ua
        }

        async with httpx.AsyncClient(
            timeout=config.REQUEST_TIMEOUT,
            follow_redirects=True,
            proxy=proxy,
            http2=True,
            verify=False,
            headers=headers
        ) as client:
            
            token = None
            tm_cookies = {}
            
            try:
                # --- Retries Loop for Account Creation ---
                max_retries = 100 if use_vpn else 3
                retry_count = 0
                flow_success = False
                
                while retry_count < max_retries:
                    if not self.is_active: return
                    try:
                        # --- 1. Register Device ---
                        try:
                            device_id = await register_device(proxy=proxy)
                            client.headers["device-id"] = device_id
                        except Exception as e:
                            logger.warning(f"⚠️ [Worker {worker_display_id}] Device Reg Failed: {e}")
                            raise e 

                        # --- 2. Temp Mail & Signup ---
                        request_time = int(time.time() * 1000)
                        
                        inbox_resp = await temp_mail_viewmodel.get_inbox(request_time)
                        inbox_data = inbox_resp.json()
                        email = inbox_data.get("data", {}).get("name")
                        tm_cookies = dict(inbox_resp.cookies)
                        
                        if not email:
                            raise Exception("No email found")
                        
                        try:
                            send_resp = await api_viewmodel.send_verification_code(email, client=client, base_url=base_url)
                        except SuperliveError as se:
                            logger.warning(f"⚠️ [Worker {worker_display_id}] Verification Error: {se}")
                            raise se

                        email_verification_id = send_resp.get("email_verification_id") or send_resp.get("data", {}).get("email_verification_id")
                        
                        if not email_verification_id:
                            raise Exception("No verification ID")
                            
                        otp = None
                        poll_start = time.time()
                        while time.time() - poll_start < 40:
                            try:
                                poll_resp = await temp_mail_viewmodel.get_inbox(int(time.time() * 1000), "us", tm_cookies)
                                otp = temp_mail_viewmodel.extract_otp(poll_resp.json())
                                if otp:
                                    break
                            except:
                                pass
                            await asyncio.sleep(2)
                            
                        if not otp:
                            raise Exception("OTP Timeout")
                            
                        await api_viewmodel.verify_email(email_verification_id, otp, client=client, base_url=base_url)
                        signup_res = await api_viewmodel.complete_signup(email, email, client=client, base_url=base_url)
                        token = signup_res.get("data", {}).get("token") or signup_res.get("token")
                        
                        if not token:
                            raise Exception("No token")
                            
                        logger.info(f"✅ [Worker {worker_display_id}] Signup Success ({email})")
                        
                        # Log to Account.txt
                        try:
                            with open("account.txt", "a") as f:
                                f.write(f"{email}\n")
                        except Exception as e:
                            logger.error(f"❌ [Worker {worker_display_id}] File Save Error: {e}")
                        
                        # Update Profile
                        try:
                            hearts = ['🧡', '💛', '💚', '💙', '💜', '🤎', '🖤', '🤍', '💔']
                            names = ['Piyush', 'Dollu', 'Jiu', 'Nishu']
                            final_name = f"{random.choice(names)} {random.choice(hearts)}"
                            await api_viewmodel.update_profile(token, name=final_name, client=client, base_url=base_url)
                            logger.info(f"👤 [Worker {worker_display_id}] Profile Updated: {final_name}")
                            await asyncio.sleep(0.5) 
                        except Exception as e:
                            logger.warning(f"⚠️ [Worker {worker_display_id}] Profile Update Failed: {e}")
                        
                        flow_success = True
                        break # Break retry loop on success
                        
                    except Exception as e:
                        retry_count += 1
                        logger.warning(f"⚠️ [Worker {worker_display_id}] Signup Flow Failed (Attempt {retry_count}/{max_retries}): {str(e)[:50]}")
                        await asyncio.sleep(2)
                
                if not flow_success:
                    logger.error(f"❌ [Worker {worker_display_id}] All {max_retries} attempts failed. Skipping.")
                    return

                # --- 3. Gift Loop (Exactly 4 gifts: 3x Paid + 1x Free) ---
                # Strategy: Send 3 gifts of ID 5141 (3 coins each), then 1 gift of ID 1 (Free)
                # Total 9 coins initial, 5141 costs 3. 3 * 3 = 9. Balance 0.
                
                # Determine Target stream ID
                if isinstance(livestream_id, list):
                    target_id = random.choice(livestream_id)
                else:
                    target_id = livestream_id

                # Send 3 Paid Gifts (ID 5141)
                for g_idx in range(3):
                    if not self.is_active: return
                    try:
                        gift_payload = {
                            "token": token,
                            "livestream_id": target_id,
                            "gift_id": 5141,
                            "gift_context": 1
                        }
                        await api_viewmodel.send_gift(token, gift_payload, client=client, base_url=base_url)
                        logger.info(f"🎁 [Worker {worker_display_id}] Paid Gift {g_idx+1}/3 Sent (ID: 5141) to {target_id}")
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                    except Exception as e:
                        logger.error(f"⚠️ [Worker {worker_display_id}] Paid Gift {g_idx+1} Failed: {e}")
                
                # Send 1 Free Gift (ID 5141) (as backup/cleanup)
                if self.is_active:
                    try:
                        gift_payload_free = {
                            "token": token,
                            "livestream_id": target_id,
                            "gift_id": 5141,
                            "gift_context": 1
                        }
                        await api_viewmodel.send_gift(token, gift_payload_free, client=client, base_url=base_url)
                        logger.info(f"🎁 [Worker {worker_display_id}] Free Gift Sent (ID: 5141) to {target_id}")
                    except Exception as e:
                        logger.error(f"⚠️ [Worker {worker_display_id}] Free Gift Failed: {e}")

                # --- 4. Cleanup ---
                try:
                    await api_viewmodel.logout(token, client=client, base_url=base_url)
                except:
                    pass
                try:
                    await temp_mail_viewmodel.delete_inbox(tm_cookies, int(time.time()*1000))
                except:
                    pass

            except Exception as e:
                logger.error(f"❌ [Worker {worker_display_id}] Account Process Error: {e}")


    async def run_auto_gift_loop(self, livestream_id, worker_count=2, use_proxy=True, superlive_base=1, name=None, custom_proxies=None, use_vpn=False):
        """
        Batched Cycle Orchestrator.
        1. Gets list of proxies (or None list if use_proxy=False).
        2. Chunks them into batches of size `worker_count`.
        3. Runs each batch in parallel.
        4. Waits ~5s between batches.
        5. Repeats indefinitely until stopped.
        """
        
        # 1. Prepare Proxies List (The Driver)
        if use_proxy:
            if custom_proxies and isinstance(custom_proxies, list) and len(custom_proxies) > 0:
                all_proxies = custom_proxies
            else:
                all_proxies = config.PROXIES or []
                
            if not all_proxies:
                logger.warning("No proxies available but use_proxy=True! Falling back to single local worker.")
                all_proxies = [None]
        else:
            # If not using proxy, we create a dummy list of None to drive the loop
            # We'll make it size 'worker_count' so we execute exactly one batch per cycle
            # effectively restarting the cycle (and thus 5s delay) after every batch of local workers.
            all_proxies = [None] * worker_count

        logger.info(f"🚀 Starting Auto Gift Loop. Total Drivers: {len(all_proxies)}. Batch Size: {worker_count}. Use Proxy: {use_proxy}")

        cycle_count = 0 
        
        while self.is_active:
            cycle_count += 1
            logger.info(f"🔄 === Starting Cycle {cycle_count} ===")
            
            total_proxies = len(all_proxies)
            # Calculate number of batches needed
            num_batches = (total_proxies + worker_count - 1) // worker_count
            if num_batches < 1: num_batches = 1
            
            for i in range(0, total_proxies, worker_count):
                if not self.is_active: break
                
                batch_proxies = all_proxies[i : i + worker_count]
                batch_size = len(batch_proxies)
                
                logger.info(f"📦 Processing Batch {i//worker_count + 1}/{num_batches} (Size: {batch_size})")
                
                tasks = []
                for idx, proxy in enumerate(batch_proxies):
                    # For local executions (proxy is None), the worker_index still increments linearly within the batch
                    current_proxy = proxy if use_proxy else None
                    
                    tasks.append(
                        self.process_single_account(
                            livestream_id=livestream_id,
                            worker_index=i + idx,
                            proxy=current_proxy,
                            superlive_base=superlive_base,
                            name=name,
                            use_vpn=use_vpn
                        )
                    )
                
                # Execute batch
                await asyncio.gather(*tasks)
                
                logger.info(f"✅ Batch {i//worker_count + 1} Completed. Sleeping 5s + jitter...")
                
                # Delay between batches
                await asyncio.sleep(5 + random.uniform(0, 2))
                
            logger.info(f"🏁 Cycle {cycle_count} Finished. Restarting...")
            await asyncio.sleep(1) 


    def start_loop(self, livestream_id, worker_count, use_proxy, superlive_base, name, custom_proxies, use_vpn=False):
        if self.is_active:
            return False, "Loop is already running"
            
        self.is_active = True
        self.current_task = asyncio.create_task(self.run_auto_gift_loop(livestream_id, worker_count, use_proxy, superlive_base, name, custom_proxies, use_vpn))
        return True, "Loop started"

    def stop_loop(self):
        self.is_active = False
        return True, "Stopping auto gift loop received"

gift_viewmodel = GiftViewModel()