# app/services/meta_service.py
import httpx
from typing import Optional

class MetaService:
    def __init__(self, access_token: str, phone_number_id: Optional[str] = None):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v18.0"

    async def send_whatsapp_message(self, to: str, content: Any, msg_type: str = "text"):
        if not self.phone_number_id:
            raise ValueError("phone_number_id is required for WhatsApp")
            
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        if msg_type == "text":
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": content}
            }
        else:
            # content is expected to be the full interactive dictionary
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": content
            }
        
        async with httpx.AsyncClient() as client:
            print(f"DEBUG: Meta API Request -> URL: {url}")
            # print(f"DEBUG: Meta API Request -> Headers: {headers}") # Hide token for security
            print(f"DEBUG: Meta API Request -> Payload: {payload}")
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=10.0)
                print(f"DEBUG: Meta API Response -> Status: {response.status_code}")
                print(f"DEBUG: Meta API Response -> Body: {response.text}")
                return response.json()
            except Exception as e:
                print(f"DEBUG: Meta API Error: {str(e)}")
                return {"error": str(e)}

    async def send_instagram_message(self, recipient_id: str, text: str):
        # Placeholder for Instagram messaging (similar to FB Messenger API)
        url = f"{self.base_url}/me/messages"
        params = {"access_token": self.access_token}
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": text}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, params=params, json=payload)
            return response.json()
