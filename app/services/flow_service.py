# app/services/flow_service.py
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.flow import Flow
from app.services.ai_service import AIService
import os

class FlowEngine:
    def __init__(self, db: AsyncSession, bot_id: int):
        self.db = db
        self.bot_id = bot_id

    async def execute_node(self, node: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        node_type = node.get("type")
        
        if node_type == "message":
            return {"type": "send_message", "content": node.get("content")}
            
        elif node_type == "ai_response":
            # Call AI Service
            ai_key = context.get("gemini_api_key")
            if not ai_key:
                 return {"type": "send_message", "content": "Error: AI Key not configured."}
                 
            ai_service = AIService(ai_key)
            business_id = context.get("business_id")
            user_msg = context.get("user_message", "")
            
            response = await ai_service.chat(self.db, business_id, user_msg)
            return {"type": "send_message", "content": response}
            
        elif node_type == "condition":
            # Simple condition logic placeholder
            pass
            
        return {"type": "error", "content": "Unknown node type"}

    async def find_next_node(self, flow: Flow, current_node_id: str, edge_label: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # Logic to follow edges
        for edge in flow.edges:
            if edge["source"] == current_node_id:
                if not edge_label or edge.get("label") == edge_label:
                    target_id = edge["target"]
                    for node in flow.nodes:
                        if node["id"] == target_id:
                            return node
        return None
