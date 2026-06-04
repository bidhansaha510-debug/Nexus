import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.groq_interface import GroqInterface
from config import NEXUS_CONFIG

def test_rotation():
    sys.stdout.reconfigure(encoding='utf-8')
    print("\n--- Testing API Key Pooling & Rotation ---")
    
    # 1. Inject multiple keys
    print("1. Injecting dummy keys to NEXUS_CONFIG...")
    NEXUS_CONFIG.groq.api_keys = [
        "fail_key_1", 
        "fail_key_2", 
        NEXUS_CONFIG.groq.api_key # The valid key is third in line
    ]
    
    # Initialize GroqInterface (it's a singleton, but we just fetch the instance)
    groq = GroqInterface()
    
    # Manually re-load keys since singleton might have already been created
    groq._api_keys = NEXUS_CONFIG.groq.api_keys
    groq._current_key_idx = 0
    groq._connected = True
    
    print(f"Loaded {len(groq._api_keys)} keys. Current index: {groq._current_key_idx}")
    print(f"Current active key config: {groq._get_current_key()[:10]}...\n")
    
    print("2. Attempting generation. The first two keys should fail with a 401 Unauthorized API error (behaving like a 429 for rotating, but our script rotation listens to 429).")
    print("Wait, our system specifically checks for 429 status codes to rotate.")
    
    # Let's mock the rotation by explicitly simulating a 429!
    # A real 429 is hard to force, so we'll mock the requests.post response internally for the first two attempts.
    
    # Save original post
    import requests
    original_post = requests.post
    
    print("Mocking `requests.post` to return 429 Too Many Requests for the first two attempts...")
    attempt_counter = 0
    
    def mocked_post(*args, **kwargs):
        nonlocal attempt_counter
        attempt_counter += 1
        
        if attempt_counter <= 2:
            print(f"  [Mock] Returning 429 inside requests_post interceptor (Attempt {attempt_counter})")
            class MockResponse:
                status_code = 429
                headers = {}
                text = "Too Many Requests"
                def json(self): return {"error": {"message": "Rate limit exceeded"}}
            return MockResponse()
        
        print(f"  [Mock] Allowing real request to pass through (Attempt {attempt_counter})")
        return original_post(*args, **kwargs)
        
    requests.post = mocked_post
    
    try:
        start_time = time.time()
        print("\n3. Sending 'Hello world' chat...")
        response = groq.chat(
            messages=[{"role": "user", "content": "Just say 'Hello world' and nothing else."}],
            max_tokens=10
        )
        
        elapsed = time.time() - start_time
        
        if response.success:
            print(f"\n✅ SUCCESS! Generation completed in {elapsed:.2f}s")
            print(f"Final output: {response.text}")
            print(f"Final Key Index: {groq._current_key_idx}")
            if groq._current_key_idx == 2:
                print("✅ Key rotation correctly advanced to index 2!")
            else:
                print("❌ Key rotation logic failed to advance properly.")
        else:
            print(f"\n❌ FAILED. Response: {response.error}")
            
    finally:
        # Restore original post
        requests.post = original_post

if __name__ == "__main__":
    test_rotation()
