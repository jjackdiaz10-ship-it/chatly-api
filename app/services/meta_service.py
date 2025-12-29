# app/services/meta_service.py
import httpx
from typing import Optional

class MetaService:
    def __init__(self, access_token: str, phone_number_id: Optional[str] = None):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v18.0"

    async def send_whatsapp_message(self, to: str, text: str):
        if not self.phone_number_id:
            raise ValueError("phone_number_id is required for WhatsApp")
            
        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            return response.json()

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
