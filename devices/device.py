import asyncio
import websockets
import json
import sys
import os

DEVICE_ID = sys.argv[1] if len(sys.argv) > 1 else "cam_1"
SERVER_URL = "ws://127.0.0.1:31567/ws/" + DEVICE_ID

async def process_updates(ws):
    async for msg in ws:
        data = json.loads(msg)
        if "update" in data:
            update = data["update"]
            patch_path = update.get("patch_path")
            print(f"[{DEVICE_ID}] Received patch: {patch_path}")
            # Simulate download/apply
            try:
                # Simulate file read
                # with open(patch_path, "r") as f:
                #     _ = f.read()
                status = "success"
                await asyncio.sleep(20)  
                print(f"[{DEVICE_ID}] Patch applied successfully.")
            
            except Exception as e:
                status = "failed"
                print(f"[{DEVICE_ID}] Patch failed: {e}")
            
            ack = {
                "status": status,
                "device_id": DEVICE_ID,
                "update": update
            }
            await ws.send(json.dumps(ack))

async def main():
    async with websockets.connect(SERVER_URL) as ws:
        await process_updates(ws)

if __name__ == "__main__":
    asyncio.run(main())