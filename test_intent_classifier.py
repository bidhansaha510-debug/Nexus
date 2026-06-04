"""
Test script for the new IntentClassifier
"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("Testing NEXUS Intent Classifier")
print("=" * 60)

# Test 1: Import
print("\n[1] Testing imports...")
try:
    from cognition.intent_classifier import IntentClassifier, ENGINE_DESCRIPTIONS, intent_classifier
    print(f"✅ IntentClassifier imported")
    print(f"✅ ENGINE_DESCRIPTIONS has {len(ENGINE_DESCRIPTIONS)} engines")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Router import
print("\n[2] Testing router integration...")
try:
    from cognition.cognitive_router import cognitive_router
    print(f"✅ cognitive_router imported")
except Exception as e:
    print(f"❌ Router import failed: {e}")
    sys.exit(1)

# Test 3: Keyword detection
print("\n[3] Testing keyword detection...")
test_cases = [
    ("Tell me a joke", "humor"),
    ("Why did this happen?", "causal"),
    ("Should I quit my job?", "decision"),
    ("What if aliens existed", "counterfactual"),
]

from cognition.intent_classifier import KeywordDetector
detector = KeywordDetector()

for user_input, expected_engine in test_cases:
    results = detector.scan(user_input)
    if results:
        top_engine = results[0].engine_key
        status = "✅" if top_engine == expected_engine else "⚠️"
        print(f"  {status} \"{user_input}\" → {top_engine} (expected: {expected_engine})")
    else:
        print(f"  ❌ \"{user_input}\" → No engines detected")

# Test 4: Implicit intent detection (semantic)
print("\n[4] Testing implicit intent detection (semantic)...")
implicit_test_cases = [
    ("My friend died yesterday", ["emotional", "wisdom"]),
    ("I'm struggling with purpose", ["philosophy", "wisdom"]),
    ("Is democracy failing?", ["ethics", "philosophy", "systems"]),
    ("How do computers actually think?", ["philosophy", "hypothesis"]),
]

for user_input, expected_engines in implicit_test_cases:
    results = intent_classifier.detect(user_input)
    if results:
        top_engines = [r.engine_key for r in results[:3]]
        matches = [e for e in expected_engines if e in top_engines]
        status = "✅" if matches else "⚠️"
        print(f"  {status} \"{user_input}\"")
        print(f"      Top engines: {top_engines}")
        print(f"      Expected one of: {expected_engines}")
    else:
        print(f"  ❌ \"{user_input}\" → No engines detected")

# Test 5: Stats
print("\n[5] Classifier stats:")
stats = intent_classifier.get_stats()
print(f"  Total classifications: {stats['total_classifications']}")
print(f"  Keyword only: {stats['keyword_only']}")
print(f"  Semantic only: {stats['semantic_only']}")
print(f"  LLM used: {stats['llm_used']}")
print(f"  Hybrid: {stats['hybrid']}")

print("\n" + "=" * 60)
print("Intent Classifier Test Complete!")
print("=" * 60)