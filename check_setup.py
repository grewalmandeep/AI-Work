"""Quick setup verification script."""

import os
import sys

def check_environment():
    """Check if environment is properly configured."""
    print("🔍 Checking ContentAlchemy Setup...\n")
    
    # Check Python version
    python_version = sys.version_info
    print(f"✅ Python Version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    if python_version < (3, 9):
        print("⚠️  Warning: Python 3.9+ recommended")
    
    # Check .env file
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        print("✅ .env file found")
        
        # Load environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            print("⚠️  python-dotenv not installed (install with: pip install python-dotenv)")
    else:
        print("❌ .env file not found")
        print("   Create .env file with your API keys (see README.md)")
        return False
    
    # Check API keys
    api_keys = {
        "OPENAI_API_KEY": "OpenAI (Required)",
        "SERP_API_KEY": "SERP (Optional)",
        "ANTHROPIC_API_KEY": "Anthropic Claude (Optional)",
        "GOOGLE_API_KEY": "Google Gemini (Optional)"
    }
    
    print("\n📋 API Keys Status:")
    for key, description in api_keys.items():
        value = os.getenv(key)
        if value and value != f"your_{key.lower()}_here":
            print(f"  ✅ {description}: Configured")
        else:
            status = "❌ Missing" if key == "OPENAI_API_KEY" else "⚠️  Not configured"
            print(f"  {status} {description}")
    
    # Check dependencies
    print("\n📦 Checking Dependencies:")
    required_packages = [
        "streamlit",
        "langgraph",
        "langchain",
        "openai",
        "requests"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (install with: pip install {package})")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages. Install with:")
        print(f"   pip install -r requirements.txt")
        return False
    
    print("\n✅ Setup looks good! You can run the app with:")
    print("   streamlit run web_app/streamlit_app.py")
    
    return True

if __name__ == "__main__":
    success = check_environment()
    sys.exit(0 if success else 1)
