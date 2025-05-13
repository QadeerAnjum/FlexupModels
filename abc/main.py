from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from diet_model import get_meal_recommendations, users_collection
from exercise_model import exercise_recommendations
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from uuid import uuid4
import pytz
from pydantic import BaseModel
from typing import Dict

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
        print(f"Received payload for UID {uid}: {payload}")

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

from fastapi import FastAPI, HTTPException
from typing import Dict
from datetime import datetime
from uuid import uuid4

@app.get("/get_progress/{uid}")
async def get_progress(uid: str):
    try:
        record = await plans_col.find_one({"uid": uid})
        if not record:
            return {"progress": []}

        plan = record.get("exercise_plan")
        if not plan:
            return {"progress": []}

        daily_calories = {}

        for week in plan.values():
            for day in week.values():
                for ex in day:
                    completed = ex.get("Completed")
                    completed_date = ex.get("CompletedDate")
                    exercise_name = ex.get("Exercises")

                    if completed and completed_date and exercise_name:
                        try:
                            # Parse the completed date
                            if isinstance(completed_date, str):
                                dt = datetime.fromisoformat(completed_date.split('T')[0])
                            elif isinstance(completed_date, datetime):
                                dt = completed_date
                            else:
                                dt = completed_date.to_datetime()

                            # 🟢 Fetch calories from recommended_exercise collection
                            rec_ex = await recommended_exercise_col.find_one({"Exercises": exercise_name})
                            calories = rec_ex.get("Calories", 0) if rec_ex else 0

                            date_str = dt.strftime('%Y-%m-%d')
                            daily_calories[date_str] = daily_calories.get(date_str, 0) + calories

                        except Exception as inner_e:
                            print(f"Error parsing or looking up calories: {completed_date} ({exercise_name}) -> {inner_e}")

        # Format result for frontend chart
        sorted_progress = sorted(daily_calories.items())
        progress = [
            {"date": date, "calories_burned": calories}
            for date, calories in sorted_progress
        ]

        print("Progress response:", progress)
        return {"progress": progress}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

