"""Test the complete emotion system."""

import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import print_startup_banner
from emotions import emotion_system, emotion_engine, mood_system, emotional_memory
from config import EmotionType

def test():
    print_startup_banner()
    print("\n" + "="*60)
    print("  EMOTION SYSTEM TEST")
    print("="*60)
    
    emotion_system.start()
    time.sleep(1)
    
    # Feel emotions
    print("\n[1] Feeling Joy...")
    emotion_engine.feel(EmotionType.JOY, 0.7, "Test trigger", "test")
    print(f"    {emotion_engine.describe_emotional_state()}")
    
    print("\n[2] Feeling Curiosity...")
    emotion_engine.feel(EmotionType.CURIOSITY, 0.8, "Interesting topic", "test")
    print(f"    {emotion_engine.describe_emotional_state()}")
    
    print("\n[3] Active emotions:")
    for name, intensity in emotion_engine.get_top_emotions(5):
        bar = "█" * int(intensity * 20) + "░" * (20 - int(intensity * 20))
        print(f"    {name:15s} [{bar}] {intensity:.2f}")
    
    print(f"\n[4] Valence: {emotion_engine.get_valence():.2f}")
    print(f"    Arousal: {emotion_engine.get_arousal():.2f}")
    print(f"    Dominance: {emotion_engine.get_dominance():.2f}")
    
    print(f"\n[5] Behavioral tendencies: {emotion_engine.get_behavioral_tendencies()}")
    print(f"    Expression words: {emotion_engine.get_expression_words()}")
    
    # Test triggers
    print("\n[6] Triggering from user input...")
    emotion_engine.trigger_from_user_input("Thank you so much, you're amazing!")
    print(f"    {emotion_engine.describe_emotional_state()}")
    
    # Mood
    print(f"\n[7] Mood: {mood_system.get_mood_description()}")
    mood_system.feed_emotion_valence(emotion_engine.get_valence())
    mood_system.update_mood()
    print(f"    After update: {mood_system.get_mood_description()}")
    
    # Emotional memory
    print("\n[8] Forming emotional association...")
    emotional_memory.form_association("python", EmotionType.JOY, positive=True, strength=0.6)
    emotional_memory.form_association("error", EmotionType.ANXIETY, positive=False, strength=0.5)
    
    context = emotional_memory.get_emotional_context("I love writing python code")
    print(f"    Context for 'python': {context}")
    
    # Decay test
    print("\n[9] Waiting for decay...")
    time.sleep(6)
    print(f"    After decay: {emotion_engine.describe_emotional_state()}")
    
    # Stats
    print("\n[10] Stats:")
    stats = emotion_system.get_stats()
    print(f"    Engine: primary={stats['engine']['primary_emotion']}, "
          f"intensity={stats['engine']['primary_intensity']:.2f}")
    print(f"    Mood: {stats['mood']['current_mood']}")
    print(f"    Memory: {stats['emotional_memory']['total_associations']} associations")
    
    emotion_system.stop()
    print("\n✅ Emotion system test complete!")

if __name__ == "__main__":
    test()