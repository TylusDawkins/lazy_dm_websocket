import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import redis

app = FastAPI()

# Allow frontend (adjust origin as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis setup
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# Track connected WebSocket clients
clients: List[WebSocket] = []

@app.get("/ping")
def ping():
    return {"status": "pong"}

@app.websocket("/ws/transcript")
async def transcript_ws(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    print(f"🔌 Client connected. Total: {len(clients)}")

    try:
        while True:
            await asyncio.sleep(0.5)

            # Pull all cleaned transcripts
            cleaned = redis_client.lrange("transcripts:cleaned", 0, -1)
            redis_client.delete("transcripts:cleaned")

            if cleaned:
                disconnected_clients = []
                for line in cleaned:
                    for client in clients:
                        try:
                            await client.send_text(line)
                        except Exception as e:
                            print(f"⚠️ Error sending to client: {e}")
                            disconnected_clients.append(client)

                # Remove all dead clients after broadcasting
                for client in disconnected_clients:
                    if client in clients:
                        clients.remove(client)
                        print(f"❌ Removed dead client. Remaining: {len(clients)}")


    except WebSocketDisconnect:
        clients.remove(websocket)
        print(f"❌ Client disconnected. Remaining: {len(clients)}")
    except Exception as e:
        print(f"❌ Error in WebSocket loop: {e}")
        if websocket in clients:
            clients.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("realtime_ws:app", host="0.0.0.0", port=8002, reload=True)
