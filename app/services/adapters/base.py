# app/services/adapters/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseEcommerceAdapter(ABC):
    def __init__(self, store_url: str, credentials: Dict[str, Any]):
        self.store_url = store_url.rstrip('/')
        self.credentials = credentials

    @abstractmethod
    async def fetch_products(self) -> List[Dict[str, Any]]:
        """
        Fetch products from the external platform and return them in a unified format.
        Unified format:
        [
            {
                "external_id": "123",
                "name": "Product Name",
                "description": "...",
                "price": 99.99,
                "metadata": {...}
            }
        ]
        """
        pass
