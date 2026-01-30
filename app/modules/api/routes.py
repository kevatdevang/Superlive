from quart import Blueprint, request, jsonify
from app.modules.api.viewmodel import api_viewmodel, SuperliveError
from app.modules.tempmail.viewmodel import temp_mail_viewmodel

import logging

logger = logging.getLogger("superlive.modules.api")

api_bp = Blueprint("api", __name__)

@api_bp.route('/login', methods=['POST'])
async def login():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Missing email or password"}), 400
            
        result = await api_viewmodel.login(email, password)
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Login route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/profile', methods=['POST'])
async def profile():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        token = data.get('token')
        if not token:
            return jsonify({"error": "Missing token"}), 400
            
        result = await api_viewmodel.get_profile(token)
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Profile route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/update-profile', methods=['POST'])
async def update_profile():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        token = data.get('token')
        name = data.get('name') # Optional custom name
        
        if not token:
            return jsonify({"error": "Missing token"}), 400
            
        result = await api_viewmodel.update_profile(token, name=name)
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Update profile route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/logout', methods=['POST'])
async def logout():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        token = data.get('token')
        if not token:
            return jsonify({"error": "Missing token"}), 400
            
        result = await api_viewmodel.logout(token)
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Logout route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/send-gift', methods=['POST'])
async def send_gift():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        token = data.get('token')
        if not token:
            return jsonify({"error": "Missing token"}), 400
            
        result = await api_viewmodel.send_gift(token, data)
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Send gift route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/signup', methods=['POST'])
async def signup():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        email = data.get('email')
        password = data.get('password')
        
        # Extract cookies from request headers
        cookies = dict(request.cookies)
        
        if not email or not password or not cookies:
            return jsonify({"error": "Missing email, password, or cookies"}), 400
            
        # 1. Send Verification Code
        logger.info(f"Step 1: Sending verification code to {email}")
        send_resp = await api_viewmodel.send_verification_code(email)
        
        # Extract email_verification_id from response
        # Try direct access or inside 'data'
        email_verification_id = send_resp.get("email_verification_id") or send_resp.get("data", {}).get("email_verification_id")
        
        if not email_verification_id:
            logger.error(f"Failed to get email_verification_id. Response: {send_resp}")
            return jsonify({"error": "Failed to get verification ID"}), 500
            
        logger.info(f"Verification ID: {email_verification_id}")
        
        # 2. Poll for OTP
        import asyncio
        import time
        logger.info("Step 2: Polling for OTP...")
        otp = None
        start_time = time.time()
        timeout = 30 # seconds
        
        while time.time() - start_time < timeout:
            request_time = int(time.time() * 1000)
            try:
                inbox_resp = await temp_mail_viewmodel.get_inbox(request_time, "us", cookies)
                inbox_data = inbox_resp.json()
                otp = temp_mail_viewmodel.extract_otp(inbox_data)
                
                if otp:
                    logger.info(f"Found OTP: {otp}")
                    break
            except Exception as w:
                 logger.warning(f"Error checking inbox: {w}")
                 
            await asyncio.sleep(3) # Wait 3 seconds before next poll
            
        if not otp:
            return jsonify({"error": "OTP timeout", "details": "Could not retrieve OTP from tempmail within timeout"}), 408
            
        # 3. Verify Email
        logger.info(f"Step 3: Verifying email with OTP {otp}")
        await api_viewmodel.verify_email(email_verification_id, otp)
        
        # 4. Complete Signup
        logger.info("Step 4: Completing signup")
        result = await api_viewmodel.complete_signup(email, password)
        
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Signup route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/livestream', methods=['POST'])
async def livestream():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        token = data.get('token')
        livestream_id = data.get('livestream_id')
        
        if not token or not livestream_id:
            return jsonify({"error": "Missing token or livestream_id"}), 400
            
        result = await api_viewmodel.get_livestream(token, livestream_id)
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Livestream route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/search', methods=['POST'])
async def search():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        # Token is optional for search
        token = data.get('token')
        search_query = data.get('search_query') or data.get('query')
        
        if not search_query:
            return jsonify({"error": "Missing search_query"}), 400
            
        result = await api_viewmodel.search_users(search_query, token=token)
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Search route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/health', methods=['GET'])
async def health():
    return jsonify({"status": "active", "message": "alive"}), 200