import sys
import time

try:
    from core.nexus_brain import NexusBrain
    from config import NEXUS_CONFIG
    import llm.groq_interface as groq_interface
    
    print("Loading brain...")
    brain = NexusBrain()
    
    # Force Groq on
    use_groq = True
    print("Forcing Groq to be ON for test")
    print(f"Groq Config Ready: {use_groq}")
    if use_groq:
        brain._llm.force_groq(True)
    
    system_prompt = "You are a helpful AI."
    messages = [
        {"role": "user", "content": "Analyze this logically: If A->B and B->C, does A->C? Briefly."}
    ]
    
    print("Sending chat request...", flush=True)
    start = time.time()
    
    try:
        response = brain._llm.chat(messages=messages, system_prompt=system_prompt)
        elapsed = time.time() - start
        
        print(f"Time: {elapsed:.2f}s")
        print(f"Success: {response.success}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error during LLM chat: {e}")
        import traceback
        traceback.print_exc()

finally:
    try:
        brain._llm.force_groq(False)
    except:
        pass
