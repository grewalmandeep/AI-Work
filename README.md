# ContentAlchemy 🪄

A production-ready AI Content Marketing Assistant powered by LangGraph multi-agent orchestration and Streamlit.

## Overview

ContentAlchemy is a sophisticated multi-agent system designed to help content marketers create high-quality, SEO-optimized content efficiently. It leverages specialized AI agents working in coordination to research, create, and optimize content across various formats.

## Features

### 🎯 Multi-Agent System
- **Query Handler**: Intelligently routes user intent to the correct workflow
- **Deep Research Agent**: Conducts comprehensive web research with source attribution
- **SEO Blog Writer**: Generates long-form, search-engine optimized blog posts
- **LinkedIn Post Writer**: Creates engaging professional social media posts with hashtag strategies
- **Image Generation Agent**: Crafts high-quality DALL-E 3 prompts and generates visuals
- **Content Strategist**: Organizes research into structured, readable formats

### 🚀 Key Capabilities
- **Multi-Turn Conversations**: Iteratively refine content based on feedback
- **Research-First Workflow**: Automatic deep research before content generation
- **Error Handling**: Robust fallback mechanisms to secondary LLM providers
- **Quality Scoring**: Automated quality assessment for brand voice and SEO compliance
- **Memory & Context**: Conversation history and context preservation across interactions

### 🎨 User Interface
- Clean Streamlit dashboard with chat interface
- Real-time content preview panels
- Quality scores and metrics visualization
- Research sources display
- Content refinement capabilities

## Architecture

```
ContentAlchemy/
├── agents/              # Specialized agent implementations
│   ├── query_handler.py
│   ├── research_agent.py
│   ├── blog_writer.py
│   ├── linkedin_writer.py
│   ├── image_agent.py
│   └── content_strategist.py
├── core/                # Orchestration and routing
│   ├── router.py
│   └── langgraph_workflow.py
├── integrations/        # API clients
│   ├── openai_client.py
│   ├── serp_client.py
│   ├── fallback_clients.py
│   └── image_client.py
├── web_app/            # Streamlit frontend
│   └── streamlit_app.py
├── requirements.txt
├── .env.example
└── README.md
```

## Installation

### Prerequisites
- Python 3.9 or higher
- API keys for required services (see Configuration)

### Setup

1. **Clone the repository** (or navigate to the project directory)
   ```bash
   cd Content_Generator
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Create a `.env` file in the project root with the following format:
   ```bash
   # .env file
   OPENAI_API_KEY=your_openai_api_key_here
   SERP_API_KEY=your_serp_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   GOOGLE_API_KEY=your_google_api_key_here
   ```
   
   Replace the placeholder values with your actual API keys:
   - `OPENAI_API_KEY` (Required) - Get from https://platform.openai.com/api-keys
   - `SERP_API_KEY` (Optional, recommended) - Get from https://serpapi.com/
   - `ANTHROPIC_API_KEY` (Optional) - Get from https://console.anthropic.com/
   - `GOOGLE_API_KEY` (Optional) - Get from https://makersuite.google.com/app/apikey

## Usage

### Starting the Application

Run the Streamlit app:

```bash
streamlit run web_app/streamlit_app.py
```

The application will open in your browser at `http://localhost:8501`

### Using ContentAlchemy

1. **Generate Content**: Type your request in the chat interface
   - Example: "Write a blog post about AI in marketing"
   - Example: "Create a LinkedIn post about remote work trends"
   - Example: "Generate an image of a modern office workspace"

2. **Research Mode**: The system automatically conducts research when needed
   - Example: "Research the latest trends in content marketing and write a blog post"

3. **Refine Content**: Iteratively improve generated content
   - Example: "Make the tone more professional"
   - Example: "Add more statistics"
   - Example: "Make it shorter"

### Workflow Example

```
User: "Write a comprehensive blog post about sustainable marketing"
  ↓
Query Handler: Classifies intent as "blog"
  ↓
Research Agent: Conducts deep research on sustainable marketing
  ↓
SEO Blog Writer: Generates optimized blog post with research integration
  ↓
Content Strategist: Quality scoring and optimization
  ↓
Output: Complete blog post with sources, meta description, and quality scores
```

## Configuration

### Required API Keys

- **OpenAI API Key**: Required for GPT-4 content generation and DALL-E 3 image generation
  - Get it from: https://platform.openai.com/api-keys

### Optional API Keys (Recommended)

- **SERP API Key**: Enables web research functionality
  - Get it from: https://serpapi.com/
  - Without this, research functionality will be limited

- **Anthropic Claude API Key**: Fallback LLM provider
  - Get it from: https://console.anthropic.com/

- **Google Gemini API Key**: Alternative fallback LLM provider (uses Gemini 2.0 Flash)
  - Get it from: https://makersuite.google.com/app/apikey

## Technical Stack

- **Multi-Agent System**: LangGraph
- **Language Model**: OpenAI GPT-4 Turbo (Primary)
- **Fallback LLMs**: Anthropic Claude 3.5 Sonnet, Google Gemini 2.0 Flash
- **Research Engine**: SERP API + GPT
- **Image Generation**: DALL-E 3
- **Content Optimization**: Custom LLM Prompts
- **Web Interface**: Streamlit
- **State Management**: LangGraph Memory (Checkpointing)
- **Language**: Python 3.9+

## Agent Workflows

### Blog Writing Workflow
1. Intent classification → "blog"
2. Research (if needed) → Web search and synthesis
3. Content generation → SEO-optimized blog post
4. Quality check → Brand voice and SEO compliance
5. Output → Formatted blog with metadata

### LinkedIn Post Workflow
1. Intent classification → "linkedin"
2. Research (if needed) → Quick research on topic
3. Post generation → Engaging post with hashtags
4. Engagement scoring → Quality assessment
5. Output → Formatted LinkedIn post

### Image Generation Workflow
1. Intent classification → "image"
2. Prompt crafting → Optimized DALL-E 3 prompt
3. Image generation → Visual creation
4. Output → Image with generation details

## Error Handling

The system includes comprehensive error handling:
- Automatic fallback to secondary LLM providers on primary failure
- Graceful degradation when optional APIs are unavailable
- Detailed error logging for debugging
- User-friendly error messages in the UI

## Best Practices

1. **Be Specific**: Provide clear, detailed requests for better results
2. **Use Research**: Request research for data-driven content
3. **Iterate**: Use refinement features to improve content iteratively
4. **Check Quality Scores**: Review quality metrics before publishing
5. **Review Sources**: Always verify research sources for accuracy

## Limitations

- API rate limits apply based on your provider plans
- Research quality depends on SERP API availability
- Image generation requires DALL-E 3 API access
- Content quality depends on prompt clarity

## Troubleshooting

### Common Issues

1. **"OPENAI_API_KEY not found"**
   - Ensure `.env` file exists and contains your API key
   - Check that the key is correctly formatted (no quotes needed)

2. **Research not working**
   - Verify SERP_API_KEY is set in `.env`
   - Check your SERP API quota

3. **Fallback LLMs not working**
   - Fallback providers are optional
   - Ensure API keys are correctly set if you want fallback support

4. **Import errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Verify Python version is 3.9+

## Contributing

This is a capstone project. For improvements or fixes:
1. Review the code structure
2. Test changes thoroughly
3. Update documentation as needed

## License

This project is for educational purposes.

## Acknowledgments

- Built with LangGraph for multi-agent orchestration
- Powered by OpenAI GPT-4 and DALL-E 3
- Research capabilities via SERP API
- UI built with Streamlit

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API key configuration
3. Check error logs in the console

---

**ContentAlchemy** - Transform your content creation workflow with AI 🚀
