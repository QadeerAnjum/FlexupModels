# notification_controller.py

from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import httpx

client = AsyncIOMotorClient("mongodb+srv://fahad:fahad_123@cluster0.bwyuy.mongodb.net/test?retryWrites=true&w=majority&appName=Cluster0")
db = client["test"]
notifications_col =db["recommended_exercise"]


async def check_and_notify_pending_exercises(uid: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://https://flexupmodels-production.up.railway.app/check_pending_exercises/{uid}")
        if response.status_code == 200:
            data = response.json()
            pending = data.get("pending", [])
            if pending:
                message = f"You have {len(pending)} pending exercises today: {', '.join(pending)}"
                await notifications_col.insert_one({
                    "uid": uid,
                    "message": message,
                    "timestamp": datetime.utcnow(),
                    "seen": False
                })
