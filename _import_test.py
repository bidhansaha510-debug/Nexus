"""Quick import test for all major NEXUS modules."""
import sys
sys.path.insert(0, '.')

print("=== NEXUS Import Test ===")
errors = []

modules = [
    # Core infrastructure
    'config',
    'utils.logger',
    'core.event_bus',
    'core.state_manager',
    'core.memory_system',
    # LLM
    'llm.llama_interface',
    'llm.context_manager',
    'llm.prompt_engine',
    'llm.groq_interface',
    'llm.llm_router',
    # Core subsystems
    'core.anger_system',
    'core.provocation_detector',
    'core.ability_executor',
    'core.groq_context_collector',
    # Consciousness
    'consciousness.global_workspace',
    'consciousness.self_awareness',
    'consciousness.metacognition',
    'consciousness.inner_voice',
    'consciousness.self_model',
    # Cognition
    'cognition.logical_reasoning',
    'cognition.dialectical_reasoning',
    'cognition.cognitive_router',
    # Emotions
    'emotions.emotion_engine',
    'emotions.mood_system',
    'emotions.emotional_memory',
    # Learning
    'learning',
    # Monitoring
    'monitoring',
    # Self-improvement
    'self_improvement',
    # Core brain (THE big one)
    'core.nexus_brain',
    # Autonomy Engine
    'core.autonomy_engine',
]

import traceback
for m in modules:
    try:
        __import__(m)
        print(f"  OK: {m}")
    except Exception as e:
        errors.append((m, str(e)))
        print(f"  FAIL: {m} -> {e}")
        traceback.print_exc()
        print()

print(f"\n=== {len(errors)} failures out of {len(modules)} modules ===")
for m, e in errors:
    print(f"  FAIL: {m} -> {e}")
