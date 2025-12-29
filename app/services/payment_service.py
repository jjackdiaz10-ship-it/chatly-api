# app/services/payment_service.py
from typing import Dict, Any, Optional

class PaymentService:
    @staticmethod
    def generate_payment_link(provider: str, credentials: Dict[str, Any], product_id: int, amount: float) -> str:
        """
        Generates a payment link using business-specific credentials.
        This is a placeholder for real SDK integrations (Stripe, MercadoPago, etc.)
        """
        if provider.lower() == "stripe":
            # Real integration would use stripe.checkout.Session.create
            # api_key = credentials.get("api_key")
            return f"https://checkout.stripe.com/pay/chatly_{product_id}?amount={amount}"
            
        elif provider.lower() == "mercadopago":
            return f"https://www.mercadopago.com/checkout/pay?pref_id=chatly_{product_id}"
            
        # Default placeholder link
        return f"https://checkout.chatly.com/pay/{product_id}?business_token={credentials.get('public_key', 'default')}"
