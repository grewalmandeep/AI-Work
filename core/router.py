"""Router for intent classification and workflow routing."""

from typing import Dict, Any
from agents.query_handler import QueryHandler


class WorkflowRouter:
    """Routes user queries to appropriate workflows."""
    
    def __init__(self):
        self.query_handler = QueryHandler()
    
    def route(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Route query to appropriate workflow. Uses context.selected_intent when provided (e.g. from UI)."""
        context = context or {}
        # If user chose "What do you want to do?" in the UI, use that intent
        selected = (context.get("selected_intent") or "").strip().lower()
        if selected in ("blog", "linkedin", "image", "strategy"):
            intent = selected
            intent_result = {"intent": intent, "confidence": 1.0, "method": "ui_selection"}
        else:
            intent_result = None
            try:
                intent_result = self.query_handler.classify_intent(query, context)
            except Exception:
                intent_result = {}
            intent_result = intent_result if isinstance(intent_result, dict) else {}
            intent = intent_result.get("intent", "blog") or "blog"

        try:
            requirements = self.query_handler.extract_content_requirements(
                query=query,
                intent=intent,
                context=context
            )
        except Exception:
            requirements = {}
        requirements = requirements if isinstance(requirements, dict) else {}

        try:
            needs_research = self.query_handler.should_conduct_research(query, intent)
        except Exception:
            needs_research = False

        return {
            "intent": intent,
            "query": query,
            "requirements": requirements,
            "needs_research": needs_research,
            "intent_confidence": intent_result.get("confidence", 0.5),
            "context": context
        }
