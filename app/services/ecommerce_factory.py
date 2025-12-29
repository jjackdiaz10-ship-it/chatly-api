# app/services/ecommerce_factory.py
from typing import Dict, Any
from app.models.ecommerce_config import EcommerceProvider
from app.services.adapters.base import BaseEcommerceAdapter
from app.services.adapters.woocommerce import WooCommerceAdapter
from app.services.adapters.shopify import ShopifyAdapter
from app.services.adapters.magento import MagentoAdapter
from app.services.adapters.prestashop import PrestaShopAdapter

class EcommerceFactory:
    @staticmethod
    def get_adapter(provider: EcommerceProvider, store_url: str, credentials: Dict[str, Any]) -> BaseEcommerceAdapter:
        if provider == EcommerceProvider.WOOCOMMERCE:
            return WooCommerceAdapter(store_url, credentials)
        elif provider == EcommerceProvider.SHOPIFY:
            return ShopifyAdapter(store_url, credentials)
        elif provider == EcommerceProvider.MAGENTO:
            return MagentoAdapter(store_url, credentials)
        elif provider == EcommerceProvider.PRESTASHOP:
            return PrestaShopAdapter(store_url, credentials)
        else:
            raise ValueError(f"Unsupported eCommerce provider: {provider}")
