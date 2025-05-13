# worker.py
import datetime
import pytz
import requests
from pymongo import MongoClient
from firebase_admin import messaging, credentials, initialize_app

# Initialize Firebase
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": os.getenv('FIREBASE_PROJECT_ID'),
    "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
    "private_key": os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),  # Fix multiline private key
    "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
    "client_id": os.getenv('FIREBASE_CLIENT_ID'),
    "auth_uri": os.getenv('FIREBASE_AUTH_URI'),
    "token_uri": os.getenv('FIREBASE_TOKEN_URI'),
    "auth_provider_x509_cert_url": os.getenv('FIREBASE_AUTH_PROVIDER_X509_CERT_URL'),
    "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL')
})
initialize_app(cred)


# MongoDB setup
client = MongoClient("mongodb+srv://fahad:fahad_123@cluster0.bwyuy.mongodb.net/test?retryWrites=true&w=majority&appName=Cluster0")
db = client.test
collection = db["recommended_exercise"]
user_collection = db["users"]  # where you store FCM tokens

# Timezone
pk_time = datetime.datetime.now(pytz.timezone('Asia/Karachi')).date()

def check_and_notify_users():
    users_to_notify = []

    for user in user_collection.find():
        uid = user["uid"]
        fcm_token = user.get("fcm_token")
        if not fcm_token:
            continue

        user_data = collection.find_one({"_id": uid})
        if not user_data:
            continue

        plan = user_data.get("exercise_plan", {})
        marked_today = False

        for week in plan.values():
            for day in week.values():
                for exercise in day:
                    completed = exercise.get("Completed", False)
                    date_str = exercise.get("CompletedDate")
                    if completed and date_str:
                        date = datetime.datetime.fromisoformat(date_str).date()
                        if date == pk_time:
                            marked_today = True
                            break
                if marked_today:
                    break
            if marked_today:
                break

        if not marked_today:
            users_to_notify.append(fcm_token)

    # Send FCM notifications
    for token in users_to_notify:
        message = messaging.Message(
            notification=messaging.Notification(
                title="Reminder: You missed today's workout!",
                body="Don't forget to complete your exercise plan today!",
            ),
            token=token,
        )
        response = messaging.send(message)
        print("Notification sent to:", token)

if __name__ == "__main__":
    check_and_notify_users()
