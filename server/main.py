import os
import json
import threading
import asyncio
import time
import logging
import redis
import pickle
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("iot-server")

def get_patch_list():
    return [name.decode() for name in redis_client.lrange("patch_files", 0, -1)]

redis_client = redis.Redis(host='redis', port=6379, db=0)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_patch_status(device_id):
    data = redis_client.get(f"patch_status:{device_id}")
    return pickle.loads(data) if data else {}

def set_patch_status(device_id, status):
    redis_client.set(f"patch_status:{device_id}", pickle.dumps(status))

def get_known_devices():
    data = redis_client.get("known_devices")
    return pickle.loads(data) if data else set()

def add_known_device(device_id):
    devices = get_known_devices()
    devices.add(device_id)
    redis_client.set("known_devices", pickle.dumps(devices))

def get_in_flight_updates(device_id):
    data = redis_client.get(f"in_flight_updates:{device_id}")
    return pickle.loads(data) if data else []

def set_in_flight_updates(device_id, updates):
    redis_client.set(f"in_flight_updates:{device_id}", pickle.dumps(updates))

connections = {}  

@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    await websocket.accept()
    connections[device_id] = websocket
    add_known_device(device_id)
    # Ensure keys exist in Redis
    set_patch_status(device_id, get_patch_status(device_id))
    set_in_flight_updates(device_id, get_in_flight_updates(device_id))
    
    logger.info(f"{device_id} connected")

    try:
        while True:
            data = await websocket.receive_text()
            ack = json.loads(data)
            logger.info(f"Received ack from {device_id}: {ack}")
            patch_file = ack["update"]["patch_file"]

            
            inflight = [p for p in get_in_flight_updates(device_id) if p["patch_file"] != patch_file]
            set_in_flight_updates(device_id, inflight)

            
            status = get_patch_status(device_id)
            if ack.get("status") == "success":
                status[patch_file] = "acked"
            else:
                status[patch_file] = "pending"
                logger.warning(f"Patch {patch_file} failed for {device_id}, will retry")
            set_patch_status(device_id, status)
    except WebSocketDisconnect:
        logger.info(f"{device_id} disconnected")
        del connections[device_id]

@app.get("/")
async def get():
    return HTMLResponse("<h1>WebSocket Server for Smart Camera Fleet</h1>")

def resend_pending_and_stale_inflight(loop):
    while True:
        time.sleep(5)
        now = time.time()
        patches = get_patch_list()
        # logger.info(f"{len(patches)} patches")
        if not patches:
            continue
        patch = patches[-1]
        for device_id in list(connections.keys()):
            status = get_patch_status(device_id)
            inflight_updates = get_in_flight_updates(device_id)
            patch_status_val = status.get(patch)
            inflight = next((p for p in inflight_updates if p["patch_file"] == patch), None)

            should_send = (
                patch_status_val is None or
                patch_status_val == "pending" or
                (patch_status_val == "in_flight" and inflight and now - inflight["timestamp"] > 60)
            )

            if should_send:
                # patch_path = os.path.join(PATCH_DIR, patch)
                update_package = {
                    "patch_file": patch,
                    "patch_path": "REDIS",
                    "timestamp": now
                }
                ws = connections.get(device_id)
                if ws:
                    asyncio.run_coroutine_threadsafe(
                        ws.send_text(json.dumps({"update": update_package})),
                        loop
                    )
                    if patch_status_val != "in_flight":
                        inflight_updates.append(update_package)
                    else:
                        for p in inflight_updates:
                            if p["patch_file"] == patch:
                                p["timestamp"] = now
                    status[patch] = "in_flight"
                    set_in_flight_updates(device_id, inflight_updates)
                    set_patch_status(device_id, status)
                    logger.info(f"[SEND/RESEND] Sent patch {patch} to {device_id}")

@app.on_event("startup")
async def start_patch_resender():
    loop = asyncio.get_running_loop()
    threading.Thread(target=resend_pending_and_stale_inflight, args=(loop,), daemon=True).start()