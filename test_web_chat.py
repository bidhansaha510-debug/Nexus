import requests
import time
import json

base_url = "http://localhost:5000"

print("1. Creating test user...")
try:
    requests.post(f"{base_url}/api/auth/signup", json={"username": "testuser", "password": "password", "display_name": "Test User"})
except:
    pass # Might already exist

print("2. Logging in...")
def test_web_chat():
    print("1. Creating test user...")
    try:
        requests.post(f"{base_url}/api/auth/signup", json={"username": "testuser", "password": "password", "display_name": "Test User"})
    except:
        pass # Might already exist

    print("2. Logging in...")
    res = requests.post(f"{base_url}/api/auth/login", json={"username": "testuser", "password": "password"})
    token = res.json().get("token")
    print(f"Token: {token}")

    headers = {"Authorization": f"Bearer {token}"}

    print("3. Sending message...")
    start_time = time.time()
    res = requests.post(f"{base_url}/api/chat/send", json={"message": "Analyze this logically: If A->B and B->C, does A->C? Briefly."}, headers=headers)

    task_id = res.json().get("task_id")
    print(f"Task ID: {task_id}")

    print("4. Polling for response...")
    MAX_POLLING_ATTEMPTS = 60 # 30 seconds total with 0.5s sleep
    for i in range(MAX_POLLING_ATTEMPTS):
        print(f"Polling attempt {i+1}...")
        
        url = f"{base_url}/api/chat/status/{task_id}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') in ('delivered', 'success', 'completed'): # Added 'completed' for consistency
                elapsed = time.time() - start_time
                print()
                print(f"--- Finished in {elapsed:.2f} seconds! ---")
                print(f"Status: {data.get('status')}")
                print(f"Response: {data.get('response')}")
                break
            elif data.get('status') == 'error':
                elapsed = time.time() - start_time
                print()
                print(f"--- Finished with ERROR in {elapsed:.2f} seconds! ---")
                print(f"Status: {data.get('status')}")
                print(f"Response: {data.get('error', 'unknown error')}")
                break
            # Still processing
        else:
            print(f"Error checking status: {response.text}")
            
        time.sleep(0.5)
    else: # This 'else' belongs to the for loop, executed if loop completes without 'break'
        print("\nTimed out waiting for response")

if __name__ == "__main__":
    test_web_chat()
