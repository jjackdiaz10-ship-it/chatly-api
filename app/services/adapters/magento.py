# app/services/adapters/magento.py
import httpx
from typing import List, Dict, Any
from app.services.adapters.base import BaseEcommerceAdapter

class MagentoAdapter(BaseEcommerceAdapter):
    async def fetch_products(self) -> List[Dict[str, Any]]:
        access_token = self.credentials.get("access_token")
        
        if not access_token:
            raise ValueError("Magento access token missing")

        url = f"{self.store_url}/rest/V1/products"
        headers = {"Authorization": f"Bearer {access_token}"}
        # Magento needs search criteria
        params = {"searchCriteria[pageSize]": 100}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code != 200:
                raise Exception(f"Magento API error: {response.text}")
            
            data = response.json()
            items = data.get("items", [])
            unified = []
            for item in items:
                unified.append({
                    "external_id": str(item["id"]),
                    "name": item["name"],
                    "description": next((a["value"] for a in item.get("custom_attributes", []) if a["attribute_code"] == "description"), ""),
                    "price": float(item.get("price") or 0),
                    "metadata": {
                        "sku": item["sku"],
                        "type_id": item.get("type_id"),
                        "updated_at": item.get("updated_at")
                    }
                })
            return unified
