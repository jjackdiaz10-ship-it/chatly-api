# scripts/test_ai_service.py
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import engine, AsyncSessionLocal
from app.services.ai_service import AIService
from app.models.business import Business
from app.models.category import Category
from app.models.product import Product
from app.models.subscription import Subscription
from app.models.plan import Plan

async def setup_test_data(db: AsyncSession):
    # Ensure a business and plan exist
    biz = await db.scalar(select(Business).limit(1))
    if not biz:
        biz = Business(name="Test Shop", email="test@shop.com")
        db.add(biz)
        await db.commit()
        await db.refresh(biz)
    
    # Check for plan
    plan = await db.scalar(select(Plan).where(Plan.name == "Iris Lite"))
    if not plan:
        plan = Plan(
            name="Iris Lite", 
            price_monthly=0, 
            price_yearly=0,
            features={"ai_model": "Gemini 1.5 Flash"}
        )
        db.add(plan)
        await db.commit()
    
    return biz.id

from sqlalchemy import select

async def run_tests():
    async with AsyncSessionLocal() as db:
        print("🚀 Starting AIService Simulation...")
        
        # 1. Setup
        biz_id = await setup_test_data(db)
        ai = AIService()
        user_phone = "123456789"
        
        # 2. Test Rule-First: Catalog
        print("\n🧪 Testing Rule-First: 'Ver catalogo'")
        resp, type = await ai.chat(db, biz_id, user_phone, "Ver catalogo")
        print(f"Response: {resp['type'] if isinstance(resp, dict) else resp}")
        assert type == "interactive" or "Catálogo" in str(resp), "Failed catalog rule"
        
        # 3. Test Greeting
        print("\n🧪 Testing Greeting: 'Hola'")
        resp, type = await ai.chat(db, biz_id, user_phone, "Hola")
        print(f"Response: {resp['body']['text'] if isinstance(resp, dict) else resp}")
        
        # 4. Test FAQ (Simulated)
        print("\n🧪 Testing FAQ (if exists)")
        resp, type = await ai.chat(db, biz_id, user_phone, "¿Cuales son los horarios?")
        print(f"Response: {resp}")

        # 5. Test AI Fallback & Learning
        print("\n🧪 Testing AI Fallback: '¿Vendes comida para unicornios?'")
        # This should trigger Gemini and log a suggestion
        resp, type = await ai.chat(db, biz_id, user_phone, "¿Vendes comida para unicornios?")
        print(f"AI Response: {resp}")
        
        print("\n✅ Simulation completed!")

if __name__ == "__main__":
    asyncio.run(run_tests())
