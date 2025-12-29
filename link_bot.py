import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.bot import Bot
from app.models.bot_channel import BotChannel
from app.models.channel import Channel # 👈 Required for mapper
from app.models.business_channel import BusinessChannel # 👈 Required for mapper

async def link_bot():
    async with AsyncSessionLocal() as db:
        # 1. Get the first active bot
        result = await db.execute(select(Bot).where(Bot.is_active == True))
        bot = result.scalar_one_or_none()
        
        if not bot:
            print("No active bot found. Please create one first.")
            return

        print(f"Linking Bot '{bot.name}' (ID: {bot.id}) to Channel ID 1...")
        
        # 2. Check if link already exists
        check = await db.execute(
            select(BotChannel).where(
                BotChannel.bot_id == bot.id, 
                BotChannel.business_channel_id == 1
            )
        )
        if check.scalar_one_or_none():
            print("Bot is already linked to Channel 1.")
            return

        # 3. Create the link
        link = BotChannel(bot_id=bot.id, business_channel_id=1)
        db.add(link)
        await db.commit()
        print("Success! Bot linked to Channel 1.")

if __name__ == "__main__":
    asyncio.run(link_bot())
