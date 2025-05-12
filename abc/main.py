from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from diet_model import get_meal_recommendations, users_collection
from exercise_model import exercise_recommendations

from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from uuid import uuid4

client = AsyncIOMotorClient("mongodb+srv://fahad:fahad_123@cluster0.bwyuy.mongodb.net/test?retryWrites=true&w=majority&appName=Cluster0")
db = client.test
chat_history_collection = db.chat_history
plans_col = db.recommended_exercise

app = FastAPI()

# Chat message model
class ChatMessage(BaseModel):
    uid: str
    conversation_id: str
    role: str
    text: str
    timestamp: datetime = datetime.utcnow()

class PlanPayload(BaseModel):
    exercise_plan: Dict[str, Any]

@app.post("/save_exercise_plan/{uid}")
async def upsert_plan(uid: str, payload: PlanPayload):
    try:
        await plans_col.update_one(
            {"uid": uid},
            {"$set": {"exercise_plan": payload.exercise_plan}},
            upsert=True
        )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_exercise_status/{uid}")
async def get_exercise_status(uid: str):
    try:
        record = await plans_col.find_one({"uid": uid})
        if not record:
            return {"uid": uid, "exercise_plan": None}
        return {"uid": uid, "exercise_plan": record.get("exercise_plan", None)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommend_meal/{uid}")
def recommend_meals(uid: str):
    try:
        user_data = users_collection.find_one({"UID": uid})
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        recommendations = get_meal_recommendations(user_data)
        return {"UID": uid, "recommendations": recommendations}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommend_exercise/{uid}")
def recommend_exercise(uid: str):
    try:
        user_data = users_collection.find_one({"UID": uid})
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        recommendations = exercise_recommendations(user_data)
        return {"UID": uid, "exercise_plan": recommendations}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save_chat/")
async def save_chat_message(chat_message: ChatMessage):
    try:
        message_entry = {
            "role": chat_message.role,
            "text": chat_message.text,
            "timestamp": chat_message.timestamp
        }

        result = await chat_history_collection.update_one(
            {"conversation_id": chat_message.conversation_id},
            {
                "$setOnInsert": {
                    "uid": chat_message.uid,
                    "conversation_id": chat_message.conversation_id
                },
                "$push": {"messages": message_entry}
            },
            upsert=True
        )

        return {
            "status": "Message saved successfully",
            "upserted_id": str(result.upserted_id) if result.upserted_id else "updated"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/load_chat/{uid}")
async def load_chat(uid: str):
    try:
        convo = await chat_history_collection.find_one({"uid": uid})
        if not convo or "messages" not in convo:
            return {"uid": uid, "chat_messages": []}

        sorted_messages = sorted(
            convo["messages"],
            key=lambda msg: msg.get("timestamp")
        )

        chat_messages = [
            {
                "role": msg["role"],
                "text": msg["text"],
                "timestamp": msg["timestamp"].strftime('%Y-%m-%d %H:%M:%S')
            }
            for msg in sorted_messages
        ]

        return {"uid": uid, "chat_messages": chat_messages}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_conversation_id/{uid}")
async def get_conversation_id(uid: str):
    try:
        existing = await chat_history_collection.find_one({"uid": uid})
        if existing:
            return {"conversation_id": existing["conversation_id"]}
        else:
            new_id = str(uuid4())
            return {"conversation_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/check_pending_exercises/{uid}")
async def check_pending_exercises(uid: str):
    try:
        record = await plans_col.find_one({"uid": uid})
        if not record or "exercise_plan" not in record:
            return {"pending": []}

        plan = record["exercise_plan"]
        today = datetime.now().strftime("%Y-%m-%d")
        pending = []

        for week in plan:
            for day in plan[week]:
                for ex in plan[week][day]:
                    completed = ex.get("Completed")
                    completed_date = ex.get("CompletedDate")
                    if not completed or completed_date != today:
                        pending.append(ex["Exercises"])

        return {"pending": pending}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
