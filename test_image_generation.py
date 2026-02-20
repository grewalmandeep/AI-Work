"""Test script for OpenAI image generation (gpt-image-1). Run from project root with .env set.

gpt-image-1 returns base64 image data (b64_json), not URLs. This test handles both url and b64_json.
"""

import os
import sys
import base64

# Load .env from project root
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

from openai import OpenAI

def main():
    client = OpenAI()

    result = client.images.generate(
        model="gpt-image-1",
        prompt="A futuristic AI dashboard with glowing graphs",
        size="1024x1024"
    )

    first = result.data[0]
    url = getattr(first, "url", None)
    b64_json = getattr(first, "b64_json", None)

    if url:
        print("Image URL:", url)
        return url
    if b64_json:
        # gpt-image-1 returns base64 only; print data URL prefix so test clearly succeeded
        data_url = f"data:image/png;base64,{b64_json[:50]}..."
        print("Image received (base64, gpt-image-1 format). Length:", len(b64_json), "chars")
        print("Data URL preview:", data_url)
        return data_url
    print("No url or b64_json in response.", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    try:
        main()
        print("Image generation test passed.")
    except Exception as e:
        print(f"Image generation test failed: {e}", file=sys.stderr)
        sys.exit(1)
