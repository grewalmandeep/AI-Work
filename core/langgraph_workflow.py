"""LangGraph workflow for ContentAlchemy orchestration with LangGraph Memory."""

import logging
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END
import operator

logger = logging.getLogger(__name__)

_TRACEBACK_FILE = None

def _get_traceback_file() -> str:
    """Path to a file where we write the last exception traceback (so finalize can read it)."""
    global _TRACEBACK_FILE
    if _TRACEBACK_FILE is None:
        import os
        _TRACEBACK_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".last_traceback.txt")
    return _TRACEBACK_FILE

def _write_traceback(tb: str) -> None:
    try:
        with open(_get_traceback_file(), "w") as f:
            f.write(tb or "")
    except Exception:
        pass

def _read_traceback() -> str:
    try:
        with open(_get_traceback_file(), "r") as f:
            return f.read()
    except Exception:
        return ""


def _safe_state(state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Ensure state is always a dict so .get() never runs on None."""
    if state is None or not isinstance(state, dict):
        return {}
    return state


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Safe .get: return default if obj is None or not a dict."""
    if obj is None or not isinstance(obj, dict):
        return default
    val = obj.get(key, default)
    return val if val is not None else default


def _safe_dict(obj: Any) -> Dict[str, Any]:
    """Return obj if it's a dict, else {} so .get() is always safe."""
    return obj if (obj is not None and isinstance(obj, dict)) else {}


# Try to import MemorySaver for state persistence
try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    # Fallback for different LangGraph versions
    try:
        from langgraph.checkpoint import MemorySaver
    except ImportError:
        MemorySaver = None
        logger.warning("MemorySaver not available. State persistence will be limited.")

from core.router import WorkflowRouter
from agents.research_agent import DeepResearchAgent
from agents.blog_writer import SEOBlogWriter
from agents.linkedin_writer import LinkedInPostWriter
from agents.image_agent import ImageGenerationAgent
from agents.content_strategist import ContentStrategist


class WorkflowState(TypedDict):
    """State for the LangGraph workflow."""
    # User input
    query: str
    intent: str
    requirements: Dict[str, Any]
    needs_research: bool
    context: Dict[str, Any]
    
    # Research data
    research_data: Optional[Dict[str, Any]]
    
    # Generated content
    blog_content: Optional[Dict[str, Any]]
    linkedin_content: Optional[Dict[str, Any]]
    image_content: Optional[Dict[str, Any]]
    strategy_content: Optional[Dict[str, Any]]
    
    # Workflow metadata
    current_step: str
    history: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    
    # Quality scores
    quality_scores: Dict[str, float]
    
    # Final output
    output: Optional[Dict[str, Any]]


class ContentAlchemyWorkflow:
    """Main workflow orchestration using LangGraph with Memory."""
    
    def __init__(self, enable_checkpointing: bool = False):
        self.router = WorkflowRouter()
        self.research_agent = DeepResearchAgent()
        self.blog_writer = SEOBlogWriter()
        self.linkedin_writer = LinkedInPostWriter()
        self.image_agent = ImageGenerationAgent()
        self.strategist = ContentStrategist()
        
        # Initialize memory/checkpointing for state persistence
        if enable_checkpointing and MemorySaver:
            try:
                self.checkpointer = MemorySaver()
            except Exception as e:
                logger.warning(f"Could not initialize MemorySaver: {e}")
                self.checkpointer = None
        else:
            self.checkpointer = None
        
        # Build the workflow graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow graph."""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("route", self._route_node)
        workflow.add_node("research", self._research_node)
        workflow.add_node("generate_blog", self._generate_blog_node)
        workflow.add_node("generate_linkedin", self._generate_linkedin_node)
        workflow.add_node("generate_image", self._generate_image_node)
        workflow.add_node("create_strategy", self._create_strategy_node)
        workflow.add_node("quality_check", self._quality_check_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # Set entry point
        workflow.set_entry_point("route")
        
        # Add conditional edges from route
        workflow.add_conditional_edges(
            "route",
            self._route_decision,
            {
                "research": "research",
                "generate_blog": "generate_blog",
                "generate_linkedin": "generate_linkedin",
                "generate_image": "generate_image",
                "create_strategy": "create_strategy"
            }
        )
        
        # Add edges from research
        workflow.add_conditional_edges(
            "research",
            self._route_to_content
        )
        
        # Add edges for content generation
        workflow.add_edge("generate_blog", "quality_check")
        workflow.add_edge("generate_linkedin", "quality_check")
        workflow.add_edge("generate_image", "finalize")
        workflow.add_edge("create_strategy", "finalize")
        workflow.add_edge("quality_check", "finalize")
        
        # Finalize is terminal
        workflow.add_edge("finalize", END)
        
        # Compile with memory/checkpointing if enabled
        if self.checkpointer:
            return workflow.compile(checkpointer=self.checkpointer)
        else:
            return workflow.compile()
    
    def _route_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Route user query to appropriate workflow."""
        state = _safe_state(state)
        try:
            query = state.get("query") or ""
            logger.info(f"Routing query: {query}")
            
            routing_result = self.router.route(
                query=query,
                context=state.get("context") or {}
            )
            routing_result = _safe_state(routing_result)
            intent = _safe_get(routing_result, "intent") or "blog"
            requirements = _safe_dict(_safe_get(routing_result, "requirements"))
            needs_research = _safe_get(routing_result, "needs_research") or False
            history = state.get("history") or []
            
            return {
                "intent": intent,
                "requirements": requirements,
                "needs_research": needs_research,
                "current_step": "routed",
                "history": history + [{
                    "step": "route",
                    "intent": intent,
                    "needs_research": needs_research
                }]
            }
        except BaseException as e:
            import traceback
            tb = traceback.format_exc()
            _write_traceback(tb)
            logger.error(f"Routing error: {e}\n{tb}")
            errors = state.get("errors") or []
            return {
                "errors": errors + [{"step": "route", "error": str(e)}],
                "current_step": "error",
                "last_traceback": tb
            }
    
    def _route_decision(self, state: WorkflowState) -> str:
        """Route decision after routing node."""
        state = _safe_state(state)
        if state.get("needs_research", False):
            return "research"
        
        # Otherwise, route directly to content generation
        return self._route_to_content(state)
    
    def _route_to_content(self, state: WorkflowState) -> str:
        """Route to appropriate content generation node based on intent."""
        state = _safe_state(state)
        intent = state.get("intent", "blog")
        
        if intent == "blog":
            return "generate_blog"
        elif intent == "linkedin":
            return "generate_linkedin"
        elif intent == "image":
            return "generate_image"
        elif intent == "strategy":
            return "create_strategy"
        else:
            # Default to blog
            return "generate_blog"
    
    def _research_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Conduct research on the topic."""
        state = _safe_state(state)
        try:
            logger.info("Conducting research...")
            requirements = _safe_dict(state.get("requirements"))
            topic = _safe_get(requirements, "topic") or state.get("query", "")
            
            research_result = self.research_agent.conduct_research(
                topic=topic,
                query=state.get("query", ""),
                num_results=10,
                depth="deep"
            )
            research_result = _safe_dict(research_result)
            return {
                "research_data": research_result if _safe_get(research_result, "success") else None,
                "current_step": "research_completed",
                "history": (state.get("history") or []) + [{
                    "step": "research",
                    "success": _safe_get(research_result, "success") or False,
                    "sources_count": len(_safe_get(research_result, "sources") or [])
                }]
            }
        except BaseException as e:
            import traceback
            tb = traceback.format_exc()
            _write_traceback(tb)
            logger.error(f"Research error: {e}\n{tb}")
            return {
                "research_data": None,
                "errors": (state.get("errors") or []) + [{"step": "research", "error": str(e)}],
                "current_step": "research_error",
                "last_traceback": tb
            }
    
    def _generate_blog_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Generate SEO blog post."""
        state = _safe_state(state)
        try:
            logger.info("Generating blog post...")
            requirements = _safe_dict(state.get("requirements"))
            topic = _safe_get(requirements, "topic") or state.get("query", "")
            
            blog_result = self.blog_writer.generate_blog_post(
                topic=topic,
                research_data=state.get("research_data"),
                requirements=requirements,
                tone=_safe_get(requirements, "tone") or "professional",
                length=_safe_get(requirements, "length") or "medium",
                target_keywords=_safe_get(requirements, "keywords") or []
            )
            blog_result = _safe_dict(blog_result)
            errors = list((state.get("errors") or []))
            if not _safe_get(blog_result, "success"):
                errors.append({
                    "step": "generate_blog",
                    "error": _safe_get(blog_result, "message") or _safe_get(blog_result, "error") or "Content generation failed"
                })
            return {
                "blog_content": blog_result if _safe_get(blog_result, "success") else None,
                "errors": errors,
                "current_step": "blog_generated",
                "history": (state.get("history") or []) + [{
                    "step": "generate_blog",
                    "success": _safe_get(blog_result, "success") or False,
                    "word_count": _safe_get(blog_result, "word_count") or 0 if _safe_get(blog_result, "success") else 0
                }]
            }
        except BaseException as e:
            import traceback
            tb = traceback.format_exc()
            _write_traceback(tb)
            logger.error(f"Blog generation error: {e}\n{tb}")
            return {
                "blog_content": None,
                "errors": (state.get("errors") or []) + [{"step": "generate_blog", "error": str(e)}],
                "current_step": "blog_error",
                "last_traceback": tb
            }
    
    def _generate_linkedin_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Generate LinkedIn post and a high-definition image for every post (clear viewpoint on topic)."""
        state = _safe_state(state)
        try:
            logger.info("Generating LinkedIn post...")
            requirements = _safe_dict(state.get("requirements"))
            topic = _safe_get(requirements, "topic") or state.get("query", "")
            
            linkedin_result = self.linkedin_writer.generate_post(
                topic=topic,
                research_data=state.get("research_data"),
                requirements=requirements,
                tone=_safe_get(requirements, "tone") or "professional",
                post_type=_safe_get(requirements, "post_type") or "standard"
            )
            linkedin_result = _safe_dict(linkedin_result)
            if not _safe_get(linkedin_result, "success"):
                return {
                    "linkedin_content": None,
                    "current_step": "linkedin_generated",
                    "history": (state.get("history") or []) + [{"step": "generate_linkedin", "success": False}]
                }
            # Step 2: Generate a high-definition image for this LinkedIn post (clear viewpoint on topic)
            logger.info("Generating high-definition image for LinkedIn post...")
            post_content_snippet = (_safe_get(linkedin_result, "content") or "")[:400]
            image_result = self.image_agent.generate_image(
                topic=topic,
                style="professional",
                context=post_content_snippet,
                size="1792x1024",
                quality="hd"
            )
            image_result = _safe_dict(image_result)
            if _safe_get(image_result, "success"):
                linkedin_result["image_url"] = image_result.get("image_url") or ""
                linkedin_result["image_prompt_used"] = image_result.get("prompt_used", "")
            else:
                # Post still succeeds; surface image error so UI can show it
                linkedin_result["image_error"] = (
                    image_result.get("message") or image_result.get("error") or "Image could not be generated"
                )
                logger.warning("LinkedIn post image generation failed: %s", linkedin_result["image_error"])
            return {
                "linkedin_content": linkedin_result,
                "current_step": "linkedin_generated",
                "history": (state.get("history") or []) + [{
                    "step": "generate_linkedin",
                    "success": True,
                    "engagement_score": _safe_get(linkedin_result, "engagement_score") or 0,
                    "image_generated": _safe_get(image_result, "success") or False
                }]
            }
        except BaseException as e:
            import traceback
            tb = traceback.format_exc()
            _write_traceback(tb)
            logger.error(f"LinkedIn generation error: {e}\n{tb}")
            return {
                "linkedin_content": None,
                "errors": (state.get("errors") or []) + [{"step": "generate_linkedin", "error": str(e)}],
                "current_step": "linkedin_error",
                "last_traceback": tb
            }
    
    def _generate_image_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Generate image. On failure, append real error so user sees it (e.g. API key, content policy)."""
        state = _safe_state(state)
        try:
            logger.info("Generating image...")
            requirements = _safe_dict(state.get("requirements"))
            topic = _safe_get(requirements, "topic") or state.get("query", "")
            style = _safe_get(requirements, "style") or "professional"
            research_data = _safe_dict(state.get("research_data"))
            summary = _safe_get(research_data, "research_summary") or ""
            context = summary[:500] if summary else None
            image_result = self.image_agent.generate_image(
                topic=topic,
                style=style,
                context=context
            )
            image_result = _safe_dict(image_result)
            errors = list(state.get("errors") or [])
            if not _safe_get(image_result, "success"):
                err_msg = (
                    _safe_get(image_result, "message") or
                    _safe_get(image_result, "error") or
                    "Image generation failed"
                )
                errors.append({"step": "generate_image", "error": str(err_msg)})
                logger.warning(f"Image generation failed: {err_msg}")
            return {
                "image_content": image_result if _safe_get(image_result, "success") else None,
                "errors": errors,
                "current_step": "image_generated",
                "history": (state.get("history") or []) + [{
                    "step": "generate_image",
                    "success": _safe_get(image_result, "success") or False
                }]
            }
        except BaseException as e:
            import traceback
            tb = traceback.format_exc()
            _write_traceback(tb)
            logger.error(f"Image generation error: {e}\n{tb}")
            return {
                "image_content": None,
                "errors": (state.get("errors") or []) + [{"step": "generate_image", "error": str(e)}],
                "current_step": "image_error",
                "last_traceback": tb
            }
    
    def _create_strategy_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Create content strategy."""
        state = _safe_state(state)
        try:
            logger.info("Creating content strategy...")
            requirements = _safe_dict(state.get("requirements"))
            topic = _safe_get(requirements, "topic") or state.get("query", "")
            
            strategy_result = self.strategist.create_content_brief(
                topic=topic,
                requirements=requirements,
                research_data=state.get("research_data")
            )
            strategy_result = _safe_dict(strategy_result)
            return {
                "strategy_content": strategy_result if _safe_get(strategy_result, "success") else None,
                "current_step": "strategy_created",
                "history": (state.get("history") or []) + [{
                    "step": "create_strategy",
                    "success": _safe_get(strategy_result, "success") or False
                }]
            }
        except BaseException as e:
            import traceback
            tb = traceback.format_exc()
            _write_traceback(tb)
            logger.error(f"Strategy creation error: {e}\n{tb}")
            return {
                "strategy_content": None,
                "errors": (state.get("errors") or []) + [{"step": "create_strategy", "error": str(e)}],
                "current_step": "strategy_error",
                "last_traceback": tb
            }
    
    def _quality_check_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Perform quality check on generated content."""
        state = _safe_state(state)
        try:
            logger.info("Performing quality check...")
            content_type = state.get("intent", "blog")
            content = None
            blog = state.get("blog_content") or {}
            linkedin = state.get("linkedin_content") or {}
            if content_type == "blog":
                content = blog.get("content", "") if isinstance(blog, dict) else ""
            elif content_type == "linkedin":
                content = linkedin.get("content", "") if isinstance(linkedin, dict) else ""
            
            if not content:
                return {
                    "quality_scores": {},
                    "current_step": "quality_check_skipped"
                }
            
            quality_result = self.strategist.analyze_content_quality(
                content=content,
                requirements=_safe_dict(state.get("requirements")),
                content_type=content_type
            )
            quality_result = _safe_dict(quality_result)
            scores = _safe_dict(_safe_get(quality_result, "scores")) if _safe_get(quality_result, "success") else {}
            return {
                "quality_scores": scores,
                "current_step": "quality_checked",
                "history": (state.get("history") or []) + [{
                    "step": "quality_check",
                    "scores": scores,
                    "overall_score": _safe_get(quality_result, "overall_score") or 0 if _safe_get(quality_result, "success") else 0
                }]
            }
        except BaseException as e:
            import traceback
            tb = traceback.format_exc()
            _write_traceback(tb)
            logger.error(f"Quality check error: {e}\n{tb}")
            return {
                "quality_scores": {},
                "errors": (state.get("errors") or []) + [{"step": "quality_check", "error": str(e)}],
                "current_step": "quality_check_error",
                "last_traceback": tb
            }
    
    def _finalize_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Finalize output and prepare response."""
        state = _safe_state(state)
        try:
            logger.info("Finalizing output...")
            intent = state.get("intent", "blog")
            content = None
            if intent == "blog":
                content = state.get("blog_content")
            elif intent == "linkedin":
                content = state.get("linkedin_content")
            elif intent == "image":
                content = state.get("image_content")
            elif intent == "strategy":
                content = state.get("strategy_content")
            
            has_content = False
            if content is not None:
                if not isinstance(content, dict):
                    has_content = True
                else:
                    has_content = bool(
                        _safe_get(content, "content") or _safe_get(content, "image_url") or _safe_get(content, "brief")
                    )
            errors = (state.get("errors") or [])
            last_error = "Content generation did not produce output."
            if errors:
                last = errors[-1] if errors else None
                if last is not None and isinstance(last, dict):
                    last_error = (
                        _safe_get(last, "error") or
                        _safe_get(last, "message") or
                        last_error
                    )
                elif last is not None:
                    last_error = str(last)
            if not last_error or not str(last_error).strip():
                last_error = "Content generation did not produce output. Check your API keys and try again."
            
            meta_tb = (_read_traceback() or state.get("last_traceback") or "").strip()
            output = {
                "intent": intent,
                "query": state.get("query", ""),
                "success": has_content,
                "content": content if has_content else None,
                "metadata": {
                    "quality_scores": (state.get("quality_scores") or {}),
                    "history": (state.get("history") or []),
                    "errors": errors,
                    "traceback": meta_tb
                }
            }
            if not has_content:
                output["error"] = last_error
            if state.get("research_data"):
                output["research"] = state.get("research_data")
            
            return {
                "output": output,
                "current_step": "completed"
            }
        except BaseException as e:
            import traceback
            tb = traceback.format_exc()
            _write_traceback(tb)
            logger.error(f"Finalization error: {e}\n{tb}")
            return {
                "output": {
                    "success": False,
                    "error": str(e),
                    "query": state.get("query", ""),
                    "metadata": {"traceback": tb}
                },
                "current_step": "finalization_error"
            }
    
    def run(
        self, 
        query: str, 
        context: Dict[str, Any] = None,
        thread_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Run the workflow with a user query and optional memory/threading support."""
        initial_state = {
            "query": query,
            "intent": "",
            "requirements": {},
            "needs_research": False,
            "context": context or {},
            "research_data": None,
            "blog_content": None,
            "linkedin_content": None,
            "image_content": None,
            "strategy_content": None,
            "current_step": "initialized",
            "history": [],
            "errors": [],
            "quality_scores": {},
            "output": None
        }
        
        try:
            # Prepare config for checkpointing if enabled
            if self.checkpointer and thread_id:
                run_config = config or {}
                run_config["configurable"] = {"thread_id": thread_id}
                # Run with checkpointing/threading support
                result = self.graph.invoke(initial_state, config=run_config)
            else:
                # Run without checkpointing (stateless)
                result = self.graph.invoke(initial_state)
            
            if result is None or not isinstance(result, dict):
                return {"success": False, "error": "Workflow returned no result.", "query": query}
            out = _safe_get(result, "output")
            if out is None or not isinstance(out, dict):
                return {"success": False, "error": "No output generated.", "query": query}
            return out
        except BaseException as e:
            import traceback
            tb = traceback.format_exc()
            _write_traceback(tb)
            if not (tb and tb.strip()):
                tb = f"Exception: {type(e).__name__}: {e}"
            logger.error(f"Workflow execution error: {e}\n{tb}")
            err_msg = str(e)
            if tb and ("NoneType" in err_msg or "attribute 'get'" in err_msg):
                lines = [l for l in tb.strip().split("\n") if l.strip()]
                tail = "\n".join(lines[-5:]) if len(lines) >= 5 else tb.strip()
                err_msg = err_msg + "\n\n[Traceback]\n" + tail
            return {
                "success": False,
                "error": err_msg,
                "query": query,
                "metadata": {"traceback": tb}
            }
    
    def get_conversation_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Retrieve conversation history for a thread using LangGraph Memory."""
        if not self.checkpointer or not thread_id:
            return []
        
        try:
            # Access checkpointed state history
            config = {"configurable": {"thread_id": thread_id}}
            # The history is maintained in the state's history field
            # This method can be extended to retrieve full checkpoint history
            return []
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
