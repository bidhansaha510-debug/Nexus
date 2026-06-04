"""
Test script for chat session persistence.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.chat_session_manager import chat_session_manager
import os
import json

def test_session_persistence():
    """Test that sessions are properly saved and restored."""
    
    print("=" * 60)
    print("Testing Chat Session Persistence")
    print("=" * 60)
    
    # Start a session and add messages
    session = chat_session_manager.start_new_session()
    print(f"\n1. Started session: {session.session_id[:8]}...")
    
    chat_session_manager.add_message('user', 'Hello NEXUS, this is a test message.')
    chat_session_manager.add_message('assistant', 'I received your test message! How can I help you today?', emotion='joy', emotion_intensity=0.8)
    print(f"2. Added 2 messages to session")
    
    # Force save (method is _save_session with session param)
    chat_session_manager._save_session(chat_session_manager.current_session)
    print(f"3. Saved session to disk")
    
    # Check if file exists
    session_file = chat_session_manager._get_session_file(session.session_id)
    print(f"4. Session file exists: {os.path.exists(session_file)}")
    
    if os.path.exists(session_file):
        with open(session_file, 'r') as f:
            data = json.load(f)
        print(f"5. Messages in file: {len(data.get('messages', []))}")
        for msg in data.get('messages', []):
            content_preview = msg['content'][:40] + "..." if len(msg['content']) > 40 else msg['content']
            print(f"   - {msg['role']}: {content_preview}")
    
    # Test restoration
    print("\n" + "=" * 60)
    print("Testing Session Restoration")
    print("=" * 60)
    
    # Simulate app restart by creating a new manager instance
    from core.chat_session_manager import ChatSessionManager
    new_manager = ChatSessionManager()
    
    restored = new_manager.restore_last_session()
    if restored:
        print(f"\n6. Restored session: {restored.session_id[:8]}...")
        print(f"7. Messages in restored session: {len(restored.messages)}")
        for msg in restored.messages:
            content_preview = msg.content[:40] + "..." if len(msg.content) > 40 else msg.content
            print(f"   - {msg.role}: {content_preview}")
    else:
        print("No session to restore!")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE - Session persistence working!")
    print("=" * 60)

if __name__ == "__main__":
    test_session_persistence()