
import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from learning.internet_browser import internet_browser
from learning.curiosity_engine import curiosity_engine, CuriositySource

def test_random_wikipedia():
    print("\n═══ Testing fetch_random_wikipedia ═══")
    page = internet_browser.fetch_random_wikipedia()
    
    if page.success:
        print(f"✅ Success! Fetched: {page.title}")
        print(f"URL: {page.url}")
        print(f"Summary: {page.summary[:100]}...")
        print(f"Word count: {page.word_count}")
        return True
    else:
        print(f"❌ Failed: {page.error}")
        return False

def test_curiosity_integration():
    print("\n═══ Testing CuriosityEngine Integration ═══")
    
    # Manually trigger the random wikipedia topic addition
    # We are accessing a private method for testing purposes
    print("Triggering _add_random_wikipedia_topic()...")
    curiosity_engine._add_random_wikipedia_topic()
    
    # Check if it was added
    topics = curiosity_engine.get_active_topics()
    found_random = False
    
    for topic in topics:
        if topic['source'] == 'random': # Enum value is "random"
            print(f"✅ Found random topic in queue: {topic['topic']}")
            print(f"Reason: {topic['reason']}")
            found_random = True
            break
            
    if not found_random:
        print("❌ No random topic found in queue (might be empty or failed).")
        # List all just in case
        print("Active topics:", [t['topic'] for t in topics])
        
    return found_random

if __name__ == "__main__":
    success_browser = test_random_wikipedia()
    success_engine = test_curiosity_integration()
    
    if success_browser and success_engine:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed.")
