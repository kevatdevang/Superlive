from quart import Blueprint, request, jsonify
from app.modules.user.viewmodel import user_viewmodel
from app.modules.api.viewmodel import SuperliveError
from app.core.mongo import mongo_service
import os
import logging

logger = logging.getLogger("superlive.modules.user")

user_bp = Blueprint("user", __name__, url_prefix="/user")

@user_bp.route('/profile', methods=['POST'])
async def get_user_profile():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        token = data.get('token')
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400
            
        # Call viewmodel with user_id as primary arg, token as optional kwarg
        result = await user_viewmodel.get_other_user_profile(user_id, token=token)
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"User profile route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@user_bp.route('/upload', methods=['GET'])
async def upload_accounts():
    try:
        if not os.path.exists("account.txt"):
             return jsonify({"message": "account.txt not found", "count": 0}), 200

        count = 0
        with open("account.txt", "r") as f:
            lines = f.readlines()
            
        for line in lines:
            email = line.strip()
            if email:
                await mongo_service.insert_email(email)
                count += 1
        
        # Clear the file after uploading
        open("account.txt", "w").close()
        
        return jsonify({"message": "Accounts uploaded successfully", "count": count}), 200
    except Exception as e:
        logger.error(f"Upload accounts error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500