from quart import Blueprint, request, jsonify
from app.modules.api.viewmodel import api_viewmodel
import logging

logger = logging.getLogger("superlive.modules.discover")

discover_bp = Blueprint("discover", __name__)

@discover_bp.route('/discover', methods=['POST'])
async def discover():
    try:
        req_data = await request.get_json(silent=True) or {}
        
        next_cursor = req_data.get('next')
        type_val = req_data.get('type', 6)
        
        # Superlive's discover endpoint seems to handle "next" as null for first page
        
        response = await api_viewmodel.get_discover(next_cursor=next_cursor, type_val=type_val)
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Discover route error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
