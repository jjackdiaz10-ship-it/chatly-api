# app/db/base.py
from app.db.base_class import Base

# IMPORTA MODELOS AQUÍ 👇
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.refresh_token import RefreshToken
from app.models.business import Business
from app.models.business_user import BusinessUser
from app.models.business_channel import BusinessChannel
from app.models.category import Category
from app.models.product import Product
from app.models.bot import Bot
from app.models.bot_channel import BotChannel
from app.models.channel import Channel
