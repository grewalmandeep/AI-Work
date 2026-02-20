# ContentAlchemy – Architecture & Flow

This document describes the **complete flow**, **architecture**, and **components** of the ContentAlchemy (Content_Generator) project.

---

## 1. Overview

**ContentAlchemy** is an AI-powered content marketing assistant that:

- Lets users choose what to create: **SEO blog posts**, **LinkedIn posts**, **high-quality images**, or **content strategies**.
- Uses a **LangGraph** multi-agent workflow to route requests, optionally run research, generate content, run quality checks, and return a single response.
- Exposes a **Streamlit** chat UI; the backend is Python with **OpenAI** (and optional **Claude** / **Gemini**) for text and **DALL·E 3** for images.

**Design goals:** Simple, human-friendly content; step-by-step flows; optional research; robust errors and LLM fallbacks.

**Latest features:**
- **FIFO request cache:** Last 3 requests (current + previous session) cached; user can **go back** to any of them from the sidebar.
- **Feedback loop:** After content is generated, if the user asks to **modify**, **rectify**, or change any part (article, post, image, or strategy), the corresponding agent applies the changes and the preview updates.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STREAMLIT WEB APP                                  │
│  (web_app/streamlit_app.py)                                                 │
│  • "What do you want to do?" → blog | linkedin | image | strategy           │
│  • FIFO cache (3 requests); "Previous searches" → go back to cached result  │
│  • Chat: new request → workflow.run(); modify/rectify → handle_refinement   │
│  • display_content_preview(output)                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CONTENT ALCHEMY WORKFLOW (LangGraph)                     │
│  (core/langgraph_workflow.py)                                               │
│  • StateGraph(WorkflowState)                                                 │
│  • Nodes: route → [research?] → generate_* → [quality_check?] → finalize   │
└─────────────────────────────────────────────────────────────────────────────┘
         │                    │                    │                    │
         ▼                    ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────────┐   ┌──────────────┐   ┌─────────────────┐
│   ROUTER     │    │  RESEARCH AGENT   │   │   AGENTS     │   │  INTEGRATIONS   │
│ (core/       │    │ (agents/          │   │ (agents/)    │   │ (integrations/) │
│  router.py)  │    │  research_agent)  │   │ blog_writer │   │ openai_client   │
│              │    │  SERP + LLM       │   │ linkedin_   │   │ image_client    │
│ QueryHandler │    │  synthesis        │   │ writer      │   │ serp_client      │
│ intent +     │    │                   │   │ image_agent │   │ fallback_clients│
│ requirements │    │                   │   │ content_    │   │ (Claude/Gemini) │
└──────────────┘    └──────────────────┘   │ strategist  │   └─────────────────┘
                                            └──────────────┘
```

---

## 3. Directory Structure

```
Content_Generator/
├── agents/                    # Specialized content & routing agents
│   ├── query_handler.py      # Intent classification + requirement extraction
│   ├── research_agent.py     # Deep research (SERP + LLM synthesis)
│   ├── blog_writer.py        # SEO blog posts
│   ├── linkedin_writer.py    # LinkedIn posts (+ optional image)
│   ├── image_agent.py        # DALL·E 3 prompt crafting + image generation
│   └── content_strategist.py # Content briefs, outlines, quality analysis
├── core/                     # Orchestration
│   ├── router.py             # WorkflowRouter: query → intent, requirements, needs_research
│   └── langgraph_workflow.py # ContentAlchemyWorkflow: graph, nodes, state
├── integrations/             # External APIs
│   ├── openai_client.py      # OpenAI chat (and primary LLM when not Claude)
│   ├── image_client.py       # DALL·E 3 images
│   ├── serp_client.py        # SERP API for research
│   └── fallback_clients.py   # Claude, Gemini, LLMOrchestrator (fallback chain)
├── web_app/
│   └── streamlit_app.py      # Streamlit UI: session state, chat, previews
├── utils/
│   └── traceback_capture.py  # Persist tracebacks for UI/errors
├── run.py                    # Entry: streamlit run web_app/streamlit_app.py
├── test_image_generation.py  # Standalone image API test (e.g. gpt-image-1)
├── project.yml               # Project config (commands, env, app entry)
├── docker-compose.yml        # Run app in Docker (port 8501)
├── Dockerfile                # Image for Streamlit app
├── .github/workflows/ci.yml  # CI: install deps, verify imports
├── requirements.txt
├── .env                      # API keys (OPENAI_API_KEY, etc.)
├── README.md
└── ARCHITECTURE.md           # This file
```

---

## 4. End-to-End Flow (Request → Response)

1. **User in Streamlit**
   - Selects intent via **“What do you want to do?”** (blog / LinkedIn / image / strategy).
   - Types a message (e.g. topic or request).
   - App sends `workflow.run(query, context)` with `context["selected_intent"]`.

2. **Router (route node)**
   - If `context.selected_intent` is set → use it as **intent**.
   - Else **QueryHandler** classifies intent (blog / linkedin / image / strategy) and extracts **requirements** (topic, tone, length, etc.).
   - Decides **needs_research** (e.g. research keywords or explicit “research” intent).

3. **Optional research**
   - If `needs_research`: **research** node runs **DeepResearchAgent** (SERP search + LLM synthesis).
   - Result stored in state as **research_data** (summary + sources).

4. **Content generation (one of)**
   - **blog** → `generate_blog` (SEOBlogWriter) → **quality_check** → **finalize**.
   - **linkedin** → `generate_linkedin` (LinkedInPostWriter + ImageGenerationAgent for post image) → **quality_check** → **finalize**.
   - **image** → `generate_image` (ImageGenerationAgent) → **finalize**.
   - **strategy** → `create_strategy` (ContentStrategist) → **finalize**.

5. **Quality check** (blog/LinkedIn only)
   - **ContentStrategist.analyze_content_quality** scores the text; scores go into state.

6. **Finalize**
   - Picks the right content from state (blog_content / linkedin_content / image_content / strategy_content).
   - Builds **output**: `{ intent, success, content, error?, metadata }`.
   - Returns to Streamlit.

7. **Streamlit**
   - Shows success/error; calls **display_content_preview(output)** (blog / LinkedIn / image / strategy).
   - For LinkedIn, preview shows **post + image** (or `image_error` if image failed).
   - **Request cache:** Successful result is appended to **request_cache** (FIFO, max 3); oldest evicted on 4th.

8. **Feedback loop (modify / rectify)**
   - If user message is a **modification request** (e.g. “change the tone”, “rectify the intro”, “make the image more professional”, “add a section about X”) and there is **current_output**, the app calls **handle_refinement(query, current_content, intent)**.
   - The right agent runs: **blog** → refine_content, **linkedin** → refine_post, **image** → refine_image_prompt + generate_image, **strategy** → refine_brief.
   - **\_apply_refined_to_output** merges the refined result back into **current_output**; **display_content_preview** runs so the user sees the updated content.

---

## 5. Workflow Graph (LangGraph)

- **State:** `WorkflowState` (query, intent, requirements, needs_research, context, research_data, blog_content, linkedin_content, image_content, strategy_content, current_step, history, errors, quality_scores, output).

- **Entry:** `route`.

- **Edges:**
  - **route** → (conditional)
    - If `needs_research` → **research**
    - Else → **generate_blog** | **generate_linkedin** | **generate_image** | **create_strategy**
  - **research** → (conditional) same content nodes by intent
  - **generate_blog** → **quality_check** → **finalize**
  - **generate_linkedin** → **quality_check** → **finalize**
  - **generate_image** → **finalize**
  - **create_strategy** → **finalize**
  - **finalize** → END

```
     [START]
        │
        ▼
    ┌───────┐
    │ route │
    └───┬───┘
        │
        ├── needs_research? ──► research ──► (by intent) ──► generate_*
        │
        └── by intent ──► generate_blog ──► quality_check ──► finalize ──► [END]
                    ──► generate_linkedin ──► quality_check ──► finalize ──► [END]
                    ──► generate_image ──────────────────────► finalize ──► [END]
                    ──► create_strategy ─────────────────────► finalize ──► [END]
```

---

## 6. Component Details

### 6.1 Router (`core/router.py`)

- **WorkflowRouter.route(query, context)**
  - Uses **context.selected_intent** from UI when present.
  - Otherwise **QueryHandler.classify_intent(query)** and **extract_content_requirements(query, intent)**.
  - **should_conduct_research(query, intent)** → boolean.
  - Returns: `intent`, `requirements`, `needs_research`, plus query/context for workflow.

### 6.2 Query Handler (`agents/query_handler.py`)

- **classify_intent**: LLM or keyword fallback → one of blog, linkedin, image, strategy, research.
- **extract_content_requirements**: LLM → topic, tone, length, target_audience, keywords, style.
- **should_conduct_research**: True for explicit research intent or research-like keywords (e.g. “latest”, “trends”) for blog.

### 6.3 Research Agent (`agents/research_agent.py`)

- **SERPClient** search → raw results.
- **LLMOrchestrator** synthesizes with source attribution → **research_summary** + **sources**.
- Output: `success`, `research_summary`, `sources`.

### 6.4 Blog Writer (`agents/blog_writer.py`)

- **SEOBlogWriter.generate_blog_post(topic, research_data, requirements, tone, length, target_keywords)**.
- Uses **LLMOrchestrator** with an SEO-focused system prompt (E-E-A-T, structure, step-by-step).
- Returns: title, meta_description, content, word_count, sources, provider.

### 6.5 LinkedIn Writer (`agents/linkedin_writer.py`)

- **LinkedInPostWriter.generate_post(topic, research_data, requirements, tone, post_type)**.
- Generates post text + hashtags; engagement score.
- **Workflow** then calls **ImageGenerationAgent** for a post image (HD, 1792x1024); image URL or `image_error` is attached to **linkedin_content**.

### 6.6 Image Agent (`agents/image_agent.py`)

- **craft_prompt(topic, style, context)** via LLM → DALL·E-friendly prompt.
- **generate_image(topic, style, size, quality, context)** → **ImageGenerationClient** (DALL·E 3).
- Returns: image_url, prompt_used, size, quality; or success=False with message/error (surfaced in workflow and UI).

### 6.7 Content Strategist (`agents/content_strategist.py`)

- **create_content_brief(topic, requirements, research_data)** → brief (objective, audience, messages, structure, SEO, metrics).
- **refine_brief(brief, feedback)** → revises the brief based on user feedback (modify, rectify, add/remove, reorder); used in the feedback loop.
- **create_content_outline**, **organize_research**, **analyze_content_quality** (used in quality_check node).

### 6.8 Integrations

- **OpenAIClient**: OpenAI chat completions (primary LLM unless `USE_CLAUDE_AS_PRIMARY=true`).
- **ImageGenerationClient**: DALL·E 3 (`dall-e-3`), sizes 1024x1024 / 1792x1024 / 1024x1792, quality standard/hd.
- **SERPClient**: External search API for research.
- **LLMOrchestrator**: Primary LLM (OpenAI or Claude) with fallback chain (e.g. OpenAI → Claude → Gemini). Uses **generate_with_fallback(...)** for all text generation.

---

## 7. State Model (WorkflowState)

| Field             | Purpose |
|-------------------|--------|
| query             | User input text |
| intent            | blog \| linkedin \| image \| strategy |
| requirements      | topic, tone, length, target_audience, keywords, style |
| needs_research    | Whether to run research node |
| context           | From UI (e.g. selected_intent, previous_queries) |
| research_data     | Output of research node (summary + sources) |
| blog_content      | Output of generate_blog |
| linkedin_content  | Output of generate_linkedin (text + optional image_url / image_error) |
| image_content     | Output of generate_image |
| strategy_content  | Output of create_strategy |
| current_step      | Step name for debugging |
| history           | List of step summaries |
| errors            | List of { step, error } for finalize to build user-facing error |
| quality_scores    | From quality_check (blog/LinkedIn) |
| output            | Final payload built in finalize |

---

## 8. Streamlit UI Flow

- **Session state:** messages, conversation_history, current_output, workflow, **selected_intent**, thread_id, **request_cache** (list of up to 3 `{ query, intent, output }`), **viewing_previous_query** (set when user goes back).
- **“What do you want to do?”** buttons set **selected_intent** (blog / linkedin / image / strategy).
- **Previous searches (sidebar):** Up to 3 cached requests; each has a “View: &lt;query&gt;” button. On click, **current_output** and **viewing_previous_query** are set and the main area shows that result (no new API call).
- On user message:
  - **Modification request:** **\_is_modification_request(text, has_current_output)** is true if the message contains refinement keywords (refine, change, update, modify, rectify, fix, rewrite, edit, rephrase, tweak, revise, add, remove, shorten, lengthen, simplify, expand, etc.) or starts with “Can you / Could you / Please / Would you”. Then **handle_refinement** runs with the appropriate agent (blog, linkedin, image, or **strategy** via **refine_brief**). **\_apply_refined_to_output** merges the result into **current_output**; **display_content_preview** shows the updated content.
  - **New request:** `workflow.run(query, context)` with `context["selected_intent"]`; on success, result is pushed to **request_cache** (FIFO: if len &gt; 3, pop oldest); then **display_content_preview(output)**.
- Previews:
  - **Blog:** title, meta description, content, word count, sources.
  - **LinkedIn:** optional post image (or image_error), then post text, hashtags, metrics.
  - **Image:** image URL, prompt used, size/quality.
  - **Strategy:** brief text.
- When viewing a cached result, an info line shows **“Viewing previous result: &lt;query&gt;”**.
- Errors from workflow (e.g. image generation failure) are shown from **output.error** and **metadata.errors**.

---

## 9. Error Handling & Resilience

- **Router:** Uses **selected_intent** when provided; otherwise LLM/keyword intent; on exception, requirements/defaults still returned.
- **Workflow nodes:** Try/except; on exception append to **state.errors** and set **last_traceback**; image node also appends API failure message to errors so finalize can show it.
- **Finalize:** If no content, **output.error** = last entry from **state.errors** (or generic message).
- **LLM:** **LLMOrchestrator** tries primary then fallbacks (e.g. OpenAI → Claude → Gemini); returns structured `{ success, content, provider }` or `{ success: False, error, message }`.
- **Image:** Empty topic/prompt guarded in agent and client; API errors returned as message/error and propagated to UI (and for LinkedIn, **image_error** on post so post still displays).

---

## 10. Configuration (.env)

- **OPENAI_API_KEY** – Required for chat and DALL·E 3.
- **SERP_API_KEY** (or similar) – For research (SERP client).
- **ANTHROPIC_API_KEY**, **GOOGLE_API_KEY** – Optional for LLM fallbacks.
- **USE_CLAUDE_AS_PRIMARY** – If set, Claude is primary LLM with OpenAI/Gemini as fallbacks.

---

## 11. Summary

- **Flow:** User selects intent in Streamlit → Router sets intent/requirements/needs_research → Optional research → One content path (blog / LinkedIn / image / strategy) → Optional quality_check → Finalize → Preview in UI. Successful results are cached (FIFO, max 3) for “Previous searches.”
- **Feedback loop:** Once content exists, user can ask to modify/rectify any part; **\_is_modification_request** detects it; **handle_refinement** calls the right agent (blog/linkedin/image/strategy); **\_apply_refined_to_output** updates **current_output**; preview refreshes.
- **Architecture:** Streamlit front-end, LangGraph state machine in core, specialized agents and integrations; single workflow state; clear separation between routing, research, generation, refinement, and presentation.
- **LinkedIn:** Always generates post; then generates an image for the post (HD); if image fails, post is still returned with **image_error** and UI shows both.

This document describes the **complete flow and architecture** of the project as implemented, including the latest updates (request cache, feedback loop, strategy refinement).
