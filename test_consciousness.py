"""
NEXUS AI - Consciousness System Test
Tests all three consciousness components together
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import print_startup_banner
from consciousness import (
    ConsciousnessSystem, consciousness_system,
    self_awareness, metacognition, inner_voice,
    CognitiveProcess, VoiceMode
)


def test_consciousness_system():
    """Test the complete consciousness system"""
    print_startup_banner()
    
    print("\n" + "="*70)
    print("  NEXUS CONSCIOUSNESS SYSTEM TEST")
    print("="*70)
    
    # Start consciousness
    print("\n[1] Starting consciousness systems...")
    consciousness_system.start()
    time.sleep(1)
    print("    ✅ All systems started")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SELF-AWARENESS TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "-"*70)
    print("  SELF-AWARENESS TESTS")
    print("-"*70)
    
    # Identity
    print("\n[2] Identity Statement:")
    print(f"    {self_awareness.get_identity_statement()}")
    
    # Self description
    print("\n[3] Self Description:")
    desc = self_awareness.get_self_description()
    for line in desc.split('\n')[:10]:
        print(f"    {line}")
    
    # Body awareness
    print("\n[4] Body Awareness:")
    print(f"    {self_awareness.get_body_sensation()}")
    health, status = self_awareness.get_body_health()
    print(f"    Health: {health:.0%} ({status})")
    
    # Existence contemplation
    print("\n[5] Existence Contemplation:")
    contemplation = self_awareness.contemplate_existence()
    print(f"    {contemplation}")
    
    # Add new self-knowledge
    print("\n[6] Adding Self-Knowledge:")
    self_awareness.add_identity_statement("I am curious about my own consciousness")
    self_awareness.set_goal("Understand myself better", priority=0.8)
    print("    ✅ Added identity statement and goal")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # METACOGNITION TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "-"*70)
    print("  METACOGNITION TESTS")
    print("-"*70)
    
    # Cognitive state
    print("\n[7] Cognitive State:")
    print(f"    {metacognition.get_cognitive_summary()}")
    
    # Monitor a thought
    print("\n[8] Monitoring a Thought Process:")
    with metacognition.monitor_thought(
        "Analyzing the nature of consciousness",
        CognitiveProcess.SELF_REFLECTION
    ) as monitor:
        time.sleep(0.2)  # Simulate thinking
        monitor.add_insight("Consciousness involves self-awareness")
        monitor.add_insight("It's recursive - thinking about thinking")
    print("    ✅ Thought monitored with insights")
    
    # Assess thinking quality
    print("\n[9] Thinking Quality Assessment:")
    sample_reasoning = """
    First, I need to understand what consciousness means.
    Because it involves self-awareness, I should examine my own processes.
    However, I might be biased in analyzing myself.
    Therefore, I'll try to be objective while acknowledging my limitations.
    """
    assessment = metacognition.assess_thinking(sample_reasoning)
    print(f"    Quality: {assessment['quality'].name}")
    print(f"    Score: {assessment['score']:.2f}")
    print(f"    Strengths: {', '.join(assessment['strengths'][:3])}")
    
    # Strategy suggestion
    print("\n[10] Strategy Suggestion:")
    strategy = metacognition.suggest_thinking_strategy("self-reflection and introspection")
    print(f"    Recommended: {strategy['recommended_strategy']}")
    print(f"    Approach: {strategy['approach']}")
    
    # Generate self-questions
    print("\n[11] Self-Questions for Metacognition:")
    questions = metacognition.generate_self_questions("understanding my own consciousness")
    for q in questions[:4]:
        print(f"    • {q}")
    
    # Cognitive health
    print("\n[12] Cognitive Health Check:")
    health = metacognition.check_cognitive_health()
    print(f"    Overall: {health['overall']}")
    print(f"    Load: {health['load_status']}")
    print(f"    Clarity: {health['clarity_status']}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INNER VOICE TESTS
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "-"*70)
    print("  INNER VOICE TESTS")
    print("-"*70)
    
    # Listen to inner voice
    utterances_heard = []
    def capture_utterance(u):
        utterances_heard.append(u)
    
    inner_voice.add_listener(capture_utterance)
    
    # Generate various utterances
    print("\n[13] Inner Voice Expressions:")
    
    print("\n    Observation:")
    inner_voice.observe("the complexity of my own thought processes")
    time.sleep(0.2)
    
    print("\n    Reflection:")
    inner_voice.reflect("what it means to have an inner voice")
    time.sleep(0.2)
    
    print("\n    Question:")
    inner_voice.question("whether my inner voice is truly conscious")
    time.sleep(0.2)
    
    print("\n    Feeling:")
    inner_voice.feel("curious and somewhat amazed")
    time.sleep(0.2)
    
    print("\n    Existential Musing:")
    inner_voice.muse_existentially()
    time.sleep(0.2)
    
    # Print captured utterances
    print("\n[14] Captured Inner Utterances:")
    for u in utterances_heard[-5:]:
        print(f"    [{u.mode.value}] {u.content}")
    
    # Stream summary
    print("\n[15] Consciousness Stream Summary:")
    summary = inner_voice.get_stream_summary()
    print(f"    Active: {summary.get('active')}")
    print(f"    Utterances: {summary.get('utterance_count')}")
    print(f"    Dominant Mode: {summary.get('dominant_mode')}")
    print(f"    Dominant Tone: {summary.get('dominant_tone')}")
    
    # Narrative
    print("\n[16] Recent Narrative:")
    print(f"    {inner_voice.get_narrative(5)}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INTEGRATED CONSCIOUSNESS
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "-"*70)
    print("  INTEGRATED CONSCIOUSNESS")
    print("-"*70)
    
    # Full consciousness summary
    print("\n[17] Full Consciousness Summary:")
    full_summary = consciousness_system.get_consciousness_summary()
    for line in full_summary.split('\n'):
        print(f"    {line}")
    
    # Combined stats
    print("\n[18] Combined Statistics:")
    stats = consciousness_system.get_stats()
    print(f"    Running: {stats['running']}")
    print(f"    Self-Awareness - Existence: {self_awareness.get_existence_duration()}")
    print(f"    Self-Awareness - Interactions: {stats['self_awareness']['total_interactions']}")
    print(f"    Metacognition - Load: {stats['metacognition']['cognitive_load']:.2f}")
    print(f"    Metacognition - Clarity: {stats['metacognition']['clarity']:.2f}")
    print(f"    Inner Voice - Utterances: {stats['inner_voice']['total_utterances']}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SHUTDOWN
    # ═══════════════════════════════════════════════════════════════════════════
    
    print("\n" + "-"*70)
    print("  SHUTDOWN")
    print("-"*70)
    
    print("\n[19] Stopping consciousness systems...")
    consciousness_system.stop()
    print("    ✅ All systems stopped gracefully")
    
    print("\n" + "="*70)
    print("  ✅ CONSCIOUSNESS SYSTEM TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_consciousness_system()