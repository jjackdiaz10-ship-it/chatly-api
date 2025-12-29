# app/services/adapters/woocommerce.py
import httpx
from typing import List, Dict, Any
from app.services.adapters.base import BaseEcommerceAdapter

class WooCommerceAdapter(BaseEcommerceAdapter):
    async def fetch_products(self) -> List[Dict[str, Any]]:
        consumer_key = self.credentials.get("consumer_key")
        consumer_secret = self.credentials.get("consumer_secret")
        
        if not consumer_key or not consumer_secret:
            raise ValueError("WooCommerce credentials missing")

        url = f"{self.store_url}/wp-json/wc/v3/products"
        auth = (consumer_key, consumer_secret)
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, auth=auth, params={"per_page": 100})
            if response.status_code != 200:
                raise Exception(f"WooCommerce API error: {response.text}")
            
            products = response.json()
            unified = []
            for p in products:
                unified.append({
                    "external_id": str(p["id"]),
                    "name": p["name"],
                    "description": p.get("description", ""),
                    "price": float(p["price"] or 0),
                    "metadata": {
                        "sku": p.get("sku"),
                        "categories": [c["name"] for c in p.get("categories", [])],
                        "permalink": p.get("permalink")
                    }
                })
            return unified
