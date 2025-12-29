# app/services/adapters/shopify.py
import httpx
from typing import List, Dict, Any
from app.services.adapters.base import BaseEcommerceAdapter

class ShopifyAdapter(BaseEcommerceAdapter):
    async def fetch_products(self) -> List[Dict[str, Any]]:
        access_token = self.credentials.get("access_token")
        
        if not access_token:
            raise ValueError("Shopify access token missing")

        # Using Shopify REST Admin API for simplicity
        url = f"{self.store_url}/admin/api/2023-10/products.json"
        headers = {"X-Shopify-Access-Token": access_token}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise Exception(f"Shopify API error: {response.text}")
            
            data = response.json()
            products = data.get("products", [])
            unified = []
            for p in products:
                # Use the first variant for price
                variant = p["variants"][0] if p.get("variants") else {}
                unified.append({
                    "external_id": str(p["id"]),
                    "name": p["title"],
                    "description": p.get("body_html", ""),
                    "price": float(variant.get("price") or 0),
                    "metadata": {
                        "sku": variant.get("sku"),
                        "vendor": p.get("vendor"),
                        "product_type": p.get("product_type"),
                        "status": p.get("status")
                    }
                })
            return unified
