"""Streamlit frontend for ContentAlchemy."""

import streamlit as st
import logging
from typing import Dict, Any, Optional, List
import sys
import os

# FIFO cache: keep last 3 requests (current + previous session); 4th request evicts oldest
REQUEST_CACHE_MAX = 3

# Project root (parent of web_app)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Load .env from project root so API keys are available before any workflow init
try:
    from dotenv import load_dotenv
    env_path = os.path.join(PROJECT_ROOT, ".env")
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed; rely on system env vars

from core.langgraph_workflow import ContentAlchemyWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="ContentAlchemy - AI Content Marketing Assistant",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .content-box {
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #ddd;
        margin: 1rem 0;
        background-color: #f9f9f9;
    }
    .success-box {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
    }
    .error-box {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
    }
    .info-box {
        background-color: #d1ecf1;
        border-color: #bee5eb;
        color: #0c5460;
    }
    </style>
""", unsafe_allow_html=True)


# Store last workflow init error for UI display (cache_resource doesn't expose exception to caller)
_workflow_error: Optional[str] = None


@st.cache_resource
def get_workflow():
    """Get or create workflow instance."""
    global _workflow_error
    _workflow_error = None
    try:
        return ContentAlchemyWorkflow()
    except Exception as e:
        _workflow_error = str(e)
        logger.error(f"Failed to initialize workflow: {e}")
        return None


def get_workflow_error() -> Optional[str]:
    """Return the last workflow initialization error, if any."""
    return _workflow_error


def initialize_session_state():
    """Initialize session state variables with LangGraph Memory support."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
    
    if "current_output" not in st.session_state:
        st.session_state.current_output = None
    
    if "workflow" not in st.session_state:
        st.session_state.workflow = get_workflow()
    
    # User's choice from "What do you want to do?" (blog, linkedin, image, strategy)
    if "selected_intent" not in st.session_state:
        st.session_state.selected_intent = "blog"
    
    # LangGraph Memory thread ID for conversation persistence
    if "thread_id" not in st.session_state:
        import uuid
        st.session_state.thread_id = str(uuid.uuid4())

    # FIFO cache of last 3 requests: [{ "query", "intent", "output" }, ...]; oldest evicted at 4th
    if "request_cache" not in st.session_state:
        st.session_state.request_cache = []

    # When user "goes back", we show this label (optional)
    if "viewing_previous_query" not in st.session_state:
        st.session_state.viewing_previous_query = None


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Never call .get on None; return default if obj is None or not a dict."""
    if obj is None or not isinstance(obj, dict):
        return default
    v = obj.get(key, default)
    return default if v is None else v


def _get_error_message(output: Optional[Dict[str, Any]]) -> str:
    """Build a user-facing error message from workflow output."""
    if output is None or not isinstance(output, dict):
        return "No output generated. Check that the workflow ran correctly."
    try:
        err = _safe_get(output, "error")
        if err and str(err).strip():
            return str(err).strip()
        meta = _safe_get(output, "metadata") or {}
        meta = meta if isinstance(meta, dict) else {}
        errors = _safe_get(meta, "errors") or []
        errors = errors if isinstance(errors, list) else []
        if errors:
            last = errors[-1]
            if last is not None and isinstance(last, dict):
                msg = _safe_get(last, "error") or _safe_get(last, "message")
                if msg and str(msg).strip():
                    return str(msg).strip()
    except Exception:
        pass
    return "Content generation failed. Check your .env API keys (OPENAI_API_KEY required) and try again."


def display_chat_message(role: str, content: str):
    """Display a chat message."""
    with st.chat_message(role):
        st.markdown(content)


def display_content_preview(output: Optional[Dict[str, Any]]):
    """Display generated content preview. Uses _safe_get so .get is never called on None."""
    output = output if (output is not None and isinstance(output, dict)) else {}
    if not _safe_get(output, "success"):
        st.error("No content generated or generation failed.")
        err = _safe_get(output, "error")
        if err:
            st.error(f"Error: {err}")
        return
    intent = _safe_get(output, "intent") or "unknown"
    content_data = _safe_get(output, "content")
    content_data = content_data if isinstance(content_data, dict) else {}
    if not content_data:
        st.info("No content data to display.")
        return
    if intent == "blog":
        display_blog_preview(content_data)
    elif intent == "linkedin":
        display_linkedin_preview(content_data)
    elif intent == "image":
        display_image_preview(content_data)
    elif intent == "strategy":
        display_strategy_preview(content_data)
    else:
        st.info("Content preview not available for this intent type.")
    metadata = _safe_get(output, "metadata") or {}
    metadata = metadata if isinstance(metadata, dict) else {}
    if _safe_get(metadata, "quality_scores"):
        display_quality_scores(_safe_get(metadata, "quality_scores"))
    if _safe_get(output, "research"):
        display_research_sources(_safe_get(output, "research"))


def display_blog_preview(content_data: Optional[Dict[str, Any]]):
    """Display blog post preview."""
    content_data = content_data if isinstance(content_data, dict) else {}
    if not content_data:
        st.warning("No blog content available.")
        return
    st.subheader("📝 Blog Post Preview")
    title = _safe_get(content_data, "title") or "Untitled"
    meta_desc = _safe_get(content_data, "meta_description") or ""
    content = _safe_get(content_data, "content") or ""
    word_count = _safe_get(content_data, "word_count") or 0
    sources = _safe_get(content_data, "sources") or []
    sources = sources if isinstance(sources, list) else []
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(f"### {title}")
        if meta_desc:
            st.caption(f"**Meta Description:** {meta_desc}")
    
    with col2:
        st.metric("Word Count", word_count)
        if _safe_get(content_data, "provider"):
            st.caption(f"Generated by: {_safe_get(content_data, 'provider', 'Unknown')}")
    
    st.markdown("---")
    st.markdown(content)
    
    if sources:
        with st.expander("📚 Research Sources"):
            for i, source in enumerate((sources or [])[:10], 1):
                source = source if isinstance(source, dict) else {}
                st.markdown(f"{i}. **{_safe_get(source, 'title', 'Untitled')}**")
                st.markdown(f"   [{_safe_get(source, 'source', 'Unknown')}]({_safe_get(source, 'url', '#')})")
                if _safe_get(source, "snippet"):
                    st.caption((_safe_get(source, "snippet") or "")[:150] + "...")


def display_linkedin_preview(content_data: Optional[Dict[str, Any]]):
    """Display LinkedIn post preview and its generated image (image generated for every LinkedIn post)."""
    content_data = content_data if isinstance(content_data, dict) else {}
    if not content_data:
        st.warning("No LinkedIn content available.")
        return
    st.subheader("💼 LinkedIn Post Preview")
    # Show generated image first when present (high-definition image for every LinkedIn post)
    image_url = _safe_get(content_data, "image_url")
    image_error = _safe_get(content_data, "image_error")
    if image_url:
        st.markdown("**🖼️ Post image (high-definition)**")
        st.image(image_url, caption="Generated image for this post — clear viewpoint on the topic", use_container_width=True)
        st.markdown("---")
    elif image_error:
        st.warning(f"**Image for this post could not be generated:** {image_error}")
        st.caption("The post content below is ready; you can add your own image or try again later.")
        st.markdown("---")
    content = _safe_get(content_data, "content") or ""
    hashtags = _safe_get(content_data, "hashtags") or []
    hashtags = hashtags if isinstance(hashtags, list) else []
    char_count = _safe_get(content_data, "character_count") or 0
    engagement_score = _safe_get(content_data, "engagement_score") or 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Character Count", char_count)
    with col2:
        st.metric("Hashtags", len(hashtags))
    with col3:
        st.metric("Engagement Score", f"{engagement_score:.1f}/10")
    
    if _safe_get(content_data, "provider"):
        st.caption(f"Generated by: {_safe_get(content_data, 'provider', 'Unknown')}")
    st.markdown("---")
    st.markdown(content)
    if hashtags:
        st.markdown("**Hashtags:**")
        st.markdown(" ".join(str(h) for h in hashtags))


def display_image_preview(content_data: Optional[Dict[str, Any]]):
    """Display image preview."""
    content_data = content_data if isinstance(content_data, dict) else {}
    if not content_data:
        st.warning("No image content available.")
        return
    st.subheader("🖼️ Generated Image")
    image_url = _safe_get(content_data, "image_url")
    prompt = _safe_get(content_data, "prompt_used") or ""
    revised_prompt = _safe_get(content_data, "revised_prompt") or ""
    
    if image_url:
        st.image(image_url, caption="Generated Image", use_container_width=True)
    else:
        st.error("Image URL not available.")
    
    with st.expander("📝 Image Generation Details"):
        st.markdown(f"**Prompt Used:** {prompt}")
        if revised_prompt:
            st.markdown(f"**Revised Prompt:** {revised_prompt}")
        st.markdown(f"**Size:** {_safe_get(content_data, 'size') or 'N/A'}")
        st.markdown(f"**Quality:** {_safe_get(content_data, 'quality') or 'N/A'}")


def display_strategy_preview(content_data: Optional[Dict[str, Any]]):
    """Display content strategy preview."""
    content_data = content_data if isinstance(content_data, dict) else {}
    if not content_data:
        st.warning("No strategy content available.")
        return
    st.subheader("📊 Content Strategy Preview")
    brief = _safe_get(content_data, "brief") or ""
    
    st.markdown(brief)


def display_quality_scores(scores: Optional[Dict[str, Any]]):
    """Display quality scores."""
    scores = scores if isinstance(scores, dict) else {}
    if not scores:
        return
    with st.expander("📊 Quality Scores"):
        cols = st.columns(len(scores))
        for i, (metric, score) in enumerate(scores.items()):
            with cols[i]:
                st.metric(metric.capitalize(), f"{score:.1f}/10")


def display_research_sources(research_data: Optional[Dict[str, Any]]):
    """Display research sources."""
    research_data = research_data if isinstance(research_data, dict) else {}
    sources = _safe_get(research_data, "sources") or []
    sources = sources if isinstance(sources, list) else []
    if not sources:
        return
    
    with st.expander("🔍 Research Sources"):
        for i, source in enumerate((sources or [])[:10], 1):
            source = source if isinstance(source, dict) else {}
            st.markdown(f"{i}. **{_safe_get(source, 'title', 'Untitled')}**")
            st.markdown(f"   [{_safe_get(source, 'source', 'Unknown')}]({_safe_get(source, 'url', '#')})")
            if _safe_get(source, "snippet"):
                st.caption((_safe_get(source, "snippet") or "")[:150] + "...")


# Keywords that indicate the user wants to modify/rectify existing content (feedback loop)
REFINEMENT_KEYWORDS = [
    "refine", "change", "update", "modify", "make it", "adjust", "improve",
    "rectify", "fix", "rewrite", "edit", "rephrase", "tweak", "revise", "correct",
    "redo", "alter", "adapt", "shorten", "lengthen", "simplify", "expand",
    "add", "remove", "replace", "tone down", "tone up", "reword", "rework",
]

def _is_modification_request(text: str, has_current_output: bool) -> bool:
    """True if user is asking to modify/rectify existing content (feedback loop)."""
    if not has_current_output or not (text or "").strip():
        return False
    lower = text.strip().lower()
    if any(kw in lower for kw in REFINEMENT_KEYWORDS):
        return True
    # "Can you / Could you / Please [do something] to the article/post/image"
    if len(lower) > 15 and any(lower.startswith(p) for p in ("can you", "could you", "please", "would you")):
        return True
    return False


def handle_refinement(query: str, current_content: Dict[str, Any], intent: str):
    """Handle content refinement: agent applies user feedback to article, image, or strategy."""
    if not current_content and intent != "strategy":
        return None
    workflow = st.session_state.workflow
    if not workflow:
        return None
    current_content = current_content or {}
    try:
        if intent == "blog":
            refined = workflow.blog_writer.refine_content(
                content=current_content.get("content", ""),
                feedback=query,
                original_requirements=current_content.get("requirements")
            )
            refined = refined or {}
            if refined.get("success"):
                return refined
        elif intent == "linkedin":
            refined = workflow.linkedin_writer.refine_post(
                content=current_content.get("content", ""),
                feedback=query
            )
            refined = refined or {}
            if refined.get("success"):
                return refined
        elif intent == "image":
            refined = workflow.image_agent.refine_image_prompt(
                original_prompt=current_content.get("prompt_used", "") or current_content.get("prompt", ""),
                feedback=query
            )
            refined = refined or {}
            if refined.get("success"):
                image_result = workflow.image_agent.generate_image(
                    topic=refined.get("refined_prompt", ""),
                    use_crafted_prompt=False
                )
                image_result = image_result or {}
                if image_result.get("success"):
                    return image_result
                return refined
        elif intent == "strategy":
            refined = workflow.strategist.refine_brief(
                brief=current_content.get("brief", ""),
                feedback=query
            )
            refined = refined or {}
            if refined.get("success"):
                return refined
        return None
    except Exception as e:
        logger.error(f"Refinement error: {e}")
        return None


def _apply_refined_to_output(current_output: Dict[str, Any], refined: Dict[str, Any], intent: str) -> None:
    """Merge refined result back into current_output so preview shows updated content."""
    if not current_output or not refined or not refined.get("success"):
        return
    co = current_output.get("content")
    if intent == "blog":
        # Keep title, meta, etc.; update content text
        if not isinstance(co, dict):
            co = {}
        current_output["content"] = {
            **co,
            "content": refined.get("content", co.get("content", "")),
            "refinements": refined.get("refinements"),
            "provider": refined.get("provider", co.get("provider")),
        }
    elif intent == "linkedin":
        if not isinstance(co, dict):
            co = {}
        current_output["content"] = {
            **co,
            "content": refined.get("content", co.get("content", "")),
            "hashtags": refined.get("hashtags", co.get("hashtags", [])),
            "character_count": len(refined.get("content", "") or co.get("content", "")),
            "refinements": refined.get("refinements"),
            "provider": refined.get("provider", co.get("provider")),
        }
    elif intent == "image":
        # Full replace with new image result
        current_output["content"] = refined
    elif intent == "strategy":
        if not isinstance(co, dict):
            co = {}
        current_output["content"] = {
            **co,
            "brief": refined.get("brief", co.get("brief", "")),
            "refinements": refined.get("refinements"),
            "provider": refined.get("provider", co.get("provider")),
        }


def main():
    """Main Streamlit application."""
    initialize_session_state()
    
    # Header
    st.markdown('<div class="main-header">✨ ContentAlchemy</div>', unsafe_allow_html=True)
    st.markdown("### AI-Powered Content Marketing Assistant")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Go back to previous search (FIFO cache of last 3 requests)
        cache: List[Dict[str, Any]] = getattr(st.session_state, "request_cache", [])
        if cache:
            st.markdown("### ⬅️ Previous searches")
            st.caption("View a result from this or the last session (last 3 kept).")
            for i, entry in enumerate(cache):
                entry = entry or {}
                q = (entry.get("query") or "")[:60]
                if len((entry.get("query") or "")) > 60:
                    q += "..."
                label = f"View: {q}"
                if st.button(label, key=f"go_back_{i}", use_container_width=True):
                    st.session_state.current_output = entry.get("output")
                    st.session_state.viewing_previous_query = entry.get("query")
                    st.rerun()
            st.markdown("---")

        # Conversation history
        if st.session_state.conversation_history:
            with st.expander("📜 Conversation History"):
                for i, entry in enumerate(reversed((st.session_state.conversation_history or [])[-5:])):
                    entry = entry or {}
                    st.text_area(
                        f"Query {len(st.session_state.conversation_history) - i}",
                        entry.get("query", ""),
                        height=50,
                        disabled=True,
                        key=f"history_{i}"
                    )
        
        # Clear conversation
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_history = []
            st.session_state.current_output = None
            st.session_state.viewing_previous_query = None
            # Keep request_cache across clears so user can still go back to last 3
            st.rerun()
        
        # Info
        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        ContentAlchemy helps you create:
        - 📝 SEO-optimized blog posts
        - 💼 Engaging LinkedIn posts
        - 🖼️ High-quality images
        - 📊 Content strategies
        
        Powered by LangGraph multi-agent orchestration.
        """)
    
    # Check if workflow is initialized
    if not st.session_state.workflow:
        st.error("⚠️ Failed to initialize workflow. Please check your API keys in the .env file.")
        err = get_workflow_error()
        if err:
            st.code(err, language=None)
        st.markdown("**Fix:** Ensure `.env` in the project root contains a valid `OPENAI_API_KEY` (and optionally SERP_API_KEY, etc.). Restart the app after editing `.env`.")
        st.stop()
    
    # What do you want to do? (matches About section)
    st.markdown("### What do you want to do?")
    st.caption("Choose one option below, then type your topic or request in the chat.")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("📝 SEO-optimized blog posts", use_container_width=True, key="btn_blog"):
            st.session_state.selected_intent = "blog"
            st.rerun()
    with col2:
        if st.button("💼 Engaging LinkedIn posts", use_container_width=True, key="btn_linkedin"):
            st.session_state.selected_intent = "linkedin"
            st.rerun()
    with col3:
        if st.button("🖼️ High-quality images", use_container_width=True, key="btn_image"):
            st.session_state.selected_intent = "image"
            st.rerun()
    with col4:
        if st.button("📊 Content strategies", use_container_width=True, key="btn_strategy"):
            st.session_state.selected_intent = "strategy"
            st.rerun()
    intent_labels = {"blog": "📝 Blog", "linkedin": "💼 LinkedIn", "image": "🖼️ Image", "strategy": "📊 Strategy"}
    st.info(f"**Current choice:** {intent_labels.get(st.session_state.selected_intent, st.session_state.selected_intent)} — You can change it by clicking a button above.")
    st.markdown("---")
    
    # Main chat interface
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for message in st.session_state.messages:
            display_chat_message(message["role"], message["content"])
        
        # User input
        user_input = st.chat_input("Ask me to create content, research a topic, or refine existing content...")
        
        if user_input:
            # Feedback loop: if user asks to modify/rectify any part of current content, agent applies changes
            output = st.session_state.current_output or {}
            intent = _safe_get(output, "intent", "")
            is_refinement = _is_modification_request(user_input, bool(output and _safe_get(output, "content")))

            if is_refinement:
                display_chat_message("user", user_input)
                st.session_state.messages.append({"role": "user", "content": user_input})

                with st.chat_message("assistant"):
                    with st.spinner("Applying your changes..."):
                        refined_content = handle_refinement(
                            query=user_input,
                            current_content=output.get("content") if isinstance(output.get("content"), dict) else (output.get("content") or {}),
                            intent=intent or "blog"
                        )
                        refined_content = refined_content if isinstance(refined_content, dict) else {}

                        if refined_content and refined_content.get("success"):
                            _apply_refined_to_output(st.session_state.current_output, refined_content, intent)
                            st.success("Content updated based on your feedback.")
                            display_content_preview(st.session_state.current_output)
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": "Content updated based on your feedback. See preview above."
                            })
                        else:
                            st.error("Could not apply changes. Try being more specific (e.g. 'make the tone lighter', 'add a section about X').")
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": "I couldn't apply those changes. Please try again with more specific feedback."
                            })
            else:
                # New content generation
                display_chat_message("user", user_input)
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                with st.chat_message("assistant"):
                    with st.spinner("Generating content... This may take a moment."):
                        try:
                            # Build context from conversation history and user's "What do you want to do?" choice
                            context = {
                                "previous_queries": [
                                    (entry or {}).get("query", "") if isinstance(entry, dict) else ""
                                    for entry in (st.session_state.conversation_history or [])[-3:]
                                ],
                                "selected_intent": st.session_state.selected_intent or "blog"
                            }
                            output = st.session_state.workflow.run(
                                query=user_input,
                                context=context,
                                thread_id=st.session_state.thread_id
                            )
                            output = output if (output is not None and isinstance(output, dict)) else {"success": False, "error": "Invalid response from workflow."}
                            if _safe_get(output, "success") and _safe_get(output, "content"):
                                st.session_state.current_output = output
                                st.session_state.viewing_previous_query = None  # New result = viewing current
                                st.session_state.conversation_history.append({"query": user_input, "output": output})
                                # FIFO cache: append new request, evict oldest if > 3
                                cache: List[Dict[str, Any]] = getattr(st.session_state, "request_cache", [])
                                cache.append({
                                    "query": user_input,
                                    "intent": _safe_get(output, "intent") or "unknown",
                                    "output": output,
                                })
                                while len(cache) > REQUEST_CACHE_MAX:
                                    cache.pop(0)
                                st.session_state.request_cache = cache
                                intent = _safe_get(output, "intent") or "unknown"
                                st.success(f"✅ {intent.capitalize()} content generated successfully!")
                                display_content_preview(output)
                                st.session_state.messages.append({"role": "assistant", "content": f"Generated {intent} content successfully! See preview above."})
                            else:
                                st.session_state.current_output = None
                                error_msg = _get_error_message(output)
                                meta = _safe_get(output, "metadata")
                                meta = meta if isinstance(meta, dict) else {}
                                tb = (_safe_get(meta, "traceback") or "").strip()
                                if not tb:
                                    try:
                                        from utils.traceback_capture import read_traceback
                                        tb = (read_traceback() or "").strip()
                                    except Exception:
                                        pass
                                if not tb and PROJECT_ROOT:
                                    try:
                                        tb_path = os.path.join(PROJECT_ROOT, ".last_traceback.txt")
                                        if os.path.isfile(tb_path):
                                            with open(tb_path, "r") as f:
                                                tb = f.read()
                                    except Exception:
                                        pass
                                st.error(f"❌ Failed to generate content: {error_msg}")
                                if tb:
                                    with st.expander("🔍 Technical details (traceback) – copy this to fix the error", expanded=True):
                                        st.code(tb, language="text")
                                    st.caption("Copy the traceback above and share it to fix the exact line.")
                                else:
                                    st.caption("No traceback was captured. Check the terminal where you ran streamlit for logs.")
                                st.session_state.messages.append({"role": "assistant", "content": f"I apologize, but I encountered an error: {error_msg}"})
                        except AttributeError as e:
                            import traceback
                            tb = traceback.format_exc()
                            logger.error(f"AttributeError in Streamlit: {e}\n{tb}")
                            st.error(f"❌ Failed to generate content: {str(e)}")
                            with st.expander("🔍 Traceback (error in app code – copy this)", expanded=True):
                                st.code(tb, language="text")
                            st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
                        except Exception as e:
                            import traceback
                            tb = traceback.format_exc()
                            logger.error(f"Workflow execution error: {e}\n{tb}")
                            st.error(f"An error occurred: {str(e)}")
                            with st.expander("🔍 Technical details (traceback) – copy this to report the bug", expanded=True):
                                st.code(tb, language="text")
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": f"I apologize, but an error occurred: {str(e)}"
                            })
    
    # Content preview section (if content exists)
    if st.session_state.current_output:
        st.markdown("---")
        if st.session_state.viewing_previous_query:
            st.info(f"**⬅️ Viewing previous result:** \"{(st.session_state.viewing_previous_query or '')[:80]}\"")
        st.markdown("## 📄 Current Content")
        display_content_preview(st.session_state.current_output)


if __name__ == "__main__":
    main()
