"""Simple runner script for ContentAlchemy."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import streamlit.web.cli as stcli
    
    # Path to streamlit app
    app_path = os.path.join(os.path.dirname(__file__), "web_app", "streamlit_app.py")
    
    # Run streamlit
    sys.argv = ["streamlit", "run", app_path]
    sys.exit(stcli.main())
