from quart import Blueprint, request, jsonify, render_template
from app.modules.gift.viewmodel import gift_viewmodel
import logging

logger = logging.getLogger("superlive.modules.gift")

gift_bp = Blueprint("gift", __name__)

@gift_bp.route('/auto/gift', methods=['GET', 'POST'])
async def auto_gift():
    if request.method == 'GET':
        return await render_template('gift.html')

    try:
        req_data = await request.get_json()
        if not req_data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        code = req_data.get('code')
        
        if code == 12:
            logger.info("Received Stop Signal (Code 12)")
            success, message = gift_viewmodel.stop_loop()
            return jsonify({"message": message}), 200

        if code == 10:
            livestream_id = req_data.get('livestream_id') or 127902815
            worker_count = req_data.get('worker', 2)
            use_proxy = req_data.get('use_proxy', True)
            name = req_data.get('name')
            custom_proxies = req_data.get('proxies') # List of strings
            superlive_base = req_data.get('base', 1)
            use_vpn = req_data.get('use_vpn', False)
            
            success, message = gift_viewmodel.start_loop(
                livestream_id, 
                worker_count, 
                use_proxy=use_proxy, 
                superlive_base=superlive_base, 
                name=name, 
                custom_proxies=custom_proxies,
                use_vpn=use_vpn
            )
            
            if success:
                return jsonify({"message": f"Auto gift loop started with {worker_count} workers (Proxy: {use_proxy}, Base: {superlive_base}, VPN: {use_vpn})"}), 200
            else:
                return jsonify({"message": message}), 200
            
        return jsonify({"error": "Invalid code. Use 10 to start, 12 to stop."}), 400
        
    except Exception as e:
        logger.error(f"Auto gift route error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500