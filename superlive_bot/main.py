import asyncio
from quart import Quart, jsonify, request
from app.viewmodels.gift_bot import GiftBotViewModel
from app.core.logger import logger

app = Quart(__name__)

# Global ViewModel instance (simplified for this use case)
# In a real app, we might instanitiate per request or use collection
vm = None

@app.before_serving
async def startup():
    global vm
    vm = GiftBotViewModel()
    logger.info("🚀 Superlive Bot Service Started")

@app.after_serving
async def shutdown():
    if vm:
        await vm.cleanup()
    logger.info("👋 Service Stopped")

@app.route("/auto/gift", methods=["POST"])
async def auto_gift_control():
    """
    Control Endpoint:
    Code 10: Start Execution (Requires: livestream_id, worker)
    Code 11: Pause Execution
    Code 12: Stop Execution
    """
    data = await request.get_json()
    code = data.get("code")
    
    if code == 10:
        # START
        livestream_id = data.get("livestream_id")
        worker = int(data.get("worker", 1))
        use_proxy = int(data.get("use_proxy", 0))
        
        if not livestream_id:
            return jsonify({"status": "error", "message": "livestream_id required for start"}), 400
            
        # Launch in background
        asyncio.create_task(vm.start_workers(livestream_id, worker, use_proxy))
        return jsonify({"status": "started", "target": livestream_id, "workers": worker, "use_proxy": use_proxy})
        
    elif code == 11:
        # PAUSE
        vm.pause_workers()
        return jsonify({"status": "paused"})
        
    elif code == 12:
        # STOP
        await vm.stop_workers()
        return jsonify({"status": "stopped"})
        
    elif code == 13:
        # RESUME (Custom addition if needed, but 10 could implicitly resume or restart)
        # Assuming 10 restarts fresh. Let's start with user request.
        # User defined: 10 start, 11 pause, 12 stop.
        # If paused, logic to resume via 10? Or maybe strict adherence to 10=Start.
        # Let's add a "Resume" check if 10 is called without new params? 
        # For now, 10 starts fresh or resets workers.
        pass

    return jsonify({"status": "error", "message": "Invalid code"}), 400

@app.route("/")
async def index():
    return jsonify({"status": "running", "service": "Superlive Gift Bot", "workers_active": len(vm.workers)})

if __name__ == "__main__":
    import hypercorn.asyncio
    from hypercorn.config import Config
    
    config = Config()
    config.bind = ["0.0.0.0:8000"]
    
    # CLI Mode for direct run
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        target = input("Enter Target ID: ")
        asyncio.run(GiftBotViewModel().run_cycle(target))
    else:
        asyncio.run(hypercorn.asyncio.serve(app, config))
