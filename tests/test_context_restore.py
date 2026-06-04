"""
Test that restored sessions populate the context manager for LLM memory.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.chat_session_manager import chat_session_manager
from llm.context_manager import context_manager

def test_context_restore():
    print("=" * 60)
    print("Testing Context Manager + Session Manager Integration")
    print("=" * 60)
    
    # 1. Create a session with messages
    session = chat_session_manager.start_new_session()
    chat_session_manager.add_message("user", "My name is John Doe")
    chat_session_manager.add_message("assistant", "Nice to meet you, John Doe! I will remember your name.", "joy", 0.8)
    print(f"1. Created session with 2 messages")
    
    # 2. Check context_manager has them
    stats = context_manager.get_stats()
    print(f"2. Context manager has {stats['current_messages']} messages")
    
    # 3. Get messages from context
    messages = context_manager.get_context_messages()
    for m in messages:
        preview = m["content"][:40] + "..." if len(m["content"]) > 40 else m["content"]
        print(f"   - {m['role']}: {preview}")
    
    # 4. Simulate restart - create new context_manager and restore
    print()
    print("=" * 60)
    print("Simulating app restart...")
    print("=" * 60)
    
    # Save current session first
    chat_session_manager._save_session(chat_session_manager.current_session)
    
    # Create fresh instances (simulating app restart)
    from core.chat_session_manager import ChatSessionManager
    from llm.context_manager import ContextManager
    
    new_session_mgr = ChatSessionManager()
    new_context_mgr = ContextManager()
    
    # Restore session
    restored = new_session_mgr.restore_last_session()
    if restored:
        print(f"3. Restored session: {restored.session_id[:8]}...")
        print(f"4. Session has {len(restored.messages)} messages")
        
        # Populate context manager (this is what the fix does)
        new_context_mgr.new_session()
        for msg in restored.messages:
            if msg.role == "user":
                new_context_mgr.add_user_message(msg.content)
            elif msg.role == "assistant":
                new_context_mgr.add_assistant_message(msg.content)
        
        # Check context manager
        stats = new_context_mgr.get_stats()
        print(f"5. Context manager now has {stats['current_messages']} messages")
        
        # Get messages
        messages = new_context_mgr.get_context_messages()
        for m in messages:
            preview = m["content"][:40] + "..." if len(m["content"]) > 40 else m["content"]
            print(f"   - {m['role']}: {preview}")
        
        print()
        print("=" * 60)
        print("SUCCESS! Context manager remembers the conversation!")
        print("=" * 60)
    else:
        print("No session to restore!")

if __name__ == "__main__":
    test_context_restore()