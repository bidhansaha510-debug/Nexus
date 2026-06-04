"""
NEXUS AI - Ollama Diagnostic Tool
Run this to identify and fix Ollama connection issues
"""

import requests
import json
import sys

OLLAMA_BASE = "http://localhost:11434"

def check_ollama():
    print("=" * 60)
    print("  NEXUS - Ollama Diagnostic Tool")
    print("=" * 60)
    
    # ─── Test 1: Is Ollama running? ───
    print("\n[1] Checking if Ollama is running...")
    try:
        r = requests.get(f"{OLLAMA_BASE}/", timeout=5)
        print(f"    ✅ Ollama is running (status: {r.status_code})")
        print(f"    Response: {r.text[:100]}")
    except requests.ConnectionError:
        print("    ❌ Ollama is NOT running!")
        print("    Fix: Open a terminal and run: ollama serve")
        return
    except Exception as e:
        print(f"    ❌ Error: {e}")
        return
    
    # ─── Test 2: List models ───
    print("\n[2] Checking available models...")
    try:
        # Try new API format first
        r = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        if r.status_code == 200:
            data = r.json()
            models = data.get("models", [])
            if models:
                print(f"    ✅ Found {len(models)} model(s):")
                for m in models:
                    name = m.get("name", "unknown")
                    size = m.get("size", 0) / (1024**3)
                    print(f"       • {name} ({size:.1f} GB)")
            else:
                print("    ⚠️  No models installed!")
                print("    Fix: Run one of these commands:")
                print("       ollama pull llama3.2")
                print("       ollama pull llama3.1")
                print("       ollama pull llama3")
                print("       ollama pull mistral")
                return
        else:
            print(f"    ⚠️  /api/tags returned {r.status_code}")
            print(f"    Response: {r.text[:200]}")
    except Exception as e:
        print(f"    ❌ Error listing models: {e}")
        return
    
    if not models:
        return
    
    # ─── Test 3: Find the right model name ───
    print("\n[3] Finding compatible model...")
    model_names = [m["name"] for m in models]
    
    # Priority order of models to try
    preferred = [
        "llama3.2:latest", "llama3.2",
        "llama3.1:latest", "llama3.1",
        "llama3:latest", "llama3",
        "llama3:8b", "llama3:8b-instruct-q4_0",
        "mistral:latest", "mistral",
        "codellama:latest", "codellama",
    ]
    
    selected_model = None
    
    # First try exact matches from preferred list
    for pref in preferred:
        if pref in model_names:
            selected_model = pref
            break
    
    # If no exact match, try partial matches
    if not selected_model:
        for pref in preferred:
            base = pref.split(":")[0]
            for available in model_names:
                if base in available:
                    selected_model = available
                    break
            if selected_model:
                break
    
    # Fall back to first available model
    if not selected_model:
        selected_model = model_names[0]
    
    print(f"    ✅ Selected model: {selected_model}")
    
    # ─── Test 4: Test /api/generate endpoint ───
    print(f"\n[4] Testing /api/generate with '{selected_model}'...")
    try:
        payload = {
            "model": selected_model,
            "prompt": "Say hello in one sentence.",
            "stream": False,
            "options": {
                "num_predict": 50,
                "temperature": 0.7
            }
        }
        r = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json=payload,
            timeout=120
        )
        if r.status_code == 200:
            data = r.json()
            response_text = data.get("response", "")
            print(f"    ✅ /api/generate WORKS!")
            print(f"    Response: {response_text[:150]}")
        else:
            print(f"    ❌ /api/generate returned {r.status_code}")
            print(f"    Body: {r.text[:300]}")
    except requests.Timeout:
        print("    ⚠️  Request timed out (model may be loading for first time)")
        print("    This is normal on first run. Try again.")
    except Exception as e:
        print(f"    ❌ Error: {e}")
    
    # ─── Test 5: Test /api/chat endpoint ───
    print(f"\n[5] Testing /api/chat with '{selected_model}'...")
    try:
        payload = {
            "model": selected_model,
            "messages": [
                {"role": "user", "content": "Say hello in one sentence."}
            ],
            "stream": False,
            "options": {
                "num_predict": 50,
                "temperature": 0.7
            }
        }
        r = requests.post(
            f"{OLLAMA_BASE}/api/chat",
            json=payload,
            timeout=120
        )
        if r.status_code == 200:
            data = r.json()
            msg = data.get("message", {}).get("content", "")
            print(f"    ✅ /api/chat WORKS!")
            print(f"    Response: {msg[:150]}")
            chat_works = True
        else:
            print(f"    ❌ /api/chat returned {r.status_code}")
            print(f"    Body: {r.text[:300]}")
            print(f"    → Will use /api/generate as fallback")
            chat_works = False
    except requests.Timeout:
        print("    ⚠️  Timed out (normal on first load)")
        chat_works = False
    except Exception as e:
        print(f"    ❌ Error: {e}")
        chat_works = False
    
    # ─── Summary ───
    print("\n" + "=" * 60)
    print("  DIAGNOSIS COMPLETE")
    print("=" * 60)
    print(f"  Model to use:    {selected_model}")
    print(f"  /api/generate:   Tested above")
    print(f"  /api/chat:       {'Available' if chat_works else 'NOT available (will use generate)'}")
    print()
    print(f"  → Update config.py LLMConfig.model_name to: \"{selected_model}\"")
    print("=" * 60)
    
    return selected_model, chat_works


if __name__ == "__main__":
    result = check_ollama()