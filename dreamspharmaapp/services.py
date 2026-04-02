import os
import firebase_admin
from firebase_admin import credentials, messaging
from django.conf import settings

def initialize_firebase():
    """Initialize Firebase Admin SDK on first use"""
    if not firebase_admin._apps:
        try:
            cred_path = os.path.join(settings.BASE_DIR, 'firebase_credentials.json')
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                print("Firebase Admin SDK initialized successfully.")
            else:
                print(f"Warning: Firebase credentials file not found at {cred_path}")
        except Exception as e:
            print(f"Failed to initialize Firebase: {e}")

# Initialize right away when imported
initialize_firebase()

def send_push_notification(user, title, body, data=None):
    """
    Send push notification to all active devices of a user
    """
    if not firebase_admin._apps:
        print("Firebase is not initialized. Cannot send notification.")
        return {"error": "Firebase not initialized"}
        
    if data is None:
        data = {}
    
    # Needs to be string dict for Firebase data payload
    data_payload = {str(k): str(v) for k, v in data.items()}
    
    devices = user.fcm_devices.filter(is_active=True)
    if not devices.exists():
        return {"success": 0, "failure": 0, "errors": "No active devices found"}
    
    tokens = [device.registration_id for device in devices]
    
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        data=data_payload,
        tokens=tokens,
    )
    
    try:
        response = messaging.send_each_for_multicast(message)
        
        # Handle failed tokens (e.g. unregister them)
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    failed_tokens.append(tokens[idx])
            
            # Deactivate failed tokens so we don't try again
            if failed_tokens:
                user.fcm_devices.filter(registration_id__in=failed_tokens).update(is_active=False)
                
        return {
            "success": response.success_count,
            "failure": response.failure_count
        }
    except Exception as e:
        print(f"Error sending push notification: {e}")
        return {"error": str(e)}
