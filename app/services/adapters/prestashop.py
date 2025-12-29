# app/services/adapters/prestashop.py
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from app.services.adapters.base import BaseEcommerceAdapter

class PrestaShopAdapter(BaseEcommerceAdapter):
    async def fetch_products(self) -> List[Dict[str, Any]]:
        api_key = self.credentials.get("api_key")
        
        if not api_key:
            raise ValueError("PrestaShop API key missing")

        # PrestaShop REST API is XML-based by default
        url = f"{self.store_url}/api/products"
        # We use display=full to get all product details in one go
        params = {
            "ws_key": api_key,
            "display": "full",
            "output_format": "JSON" # If supported/configured, otherwise we'd parse XML
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            if response.status_code != 200:
                raise Exception(f"PrestaShop API error: {response.text}")
            
            data = response.json()
            products = data.get("products", [])
            unified = []
            for p in products:
                # PrestaShop name/description are often localized
                name = p.get("name", "")
                if isinstance(name, list): name = name[0].get("value", "")
                
                description = p.get("description", "")
                if isinstance(description, list): description = description[0].get("value", "")

                unified.append({
                    "external_id": str(p["id"]),
                    "name": name,
                    "description": description,
                    "price": float(p.get("price") or 0),
                    "metadata": {
                        "reference": p.get("reference"),
                        "active": p.get("active"),
                        "id_category_default": p.get("id_category_default")
                    }
                })
            return unified
