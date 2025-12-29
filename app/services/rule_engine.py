# app/services/rule_engine.py
import re
from typing import List, Dict, Any, Optional

class RuleEngine:
    @staticmethod
    def match(user_message: str, rule_set: List[Dict[str, Any]]) -> Optional[str]:
        """
        Matches user message against a list of rule dictionaries.
        rule_set example: [{"pattern": r"hola|buenos dias", "response": "¡Hola! ¿Cómo estás?"}]
        """
        user_message = user_message.lower().strip()
        
        for rule in rule_set:
            pattern = rule.get("pattern", "")
            response = rule.get("response", "")
            
            if not pattern or not response:
                continue
                
            try:
                if re.search(pattern.lower(), user_message):
                    return response
            except re.error:
                # Fallback to simple string inclusion if regex is invalid
                if pattern.lower() in user_message:
                    return response
        
        return None
