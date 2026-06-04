
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.getcwd())

from config import NEXUS_CONFIG
from pyngrok import ngrok, conf

def test_ngrok():
    print("Testing Ngrok connection...")
    token = NEXUS_CONFIG.web.ngrok_auth_token
    print(f"Token: {token[:4]}...{token[-4:]}")
    
    try:
        conf.get_default().auth_token = token
        # Try to connect
        tunnel = ngrok.connect(5000)
        print(f"SUCCESS: Tunnel created at {tunnel.public_url}")
        ngrok.disconnect(tunnel.public_url)
    except Exception as e:
        print(f"ERROR: Ngrok failed: {e}")

if __name__ == "__main__":
    test_ngrok()
