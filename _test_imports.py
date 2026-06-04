"""Quick import + start test for NEXUS subsystems."""
import sys, traceback, io, os, logging

# Force UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Suppress all log output for clean testing
logging.disable(logging.CRITICAL)

print("=" * 60)
print("  NEXUS IMPORT & START DIAGNOSTICS")
print("=" * 60)

# Phase 1: Core imports
core_modules = [
    ('config', 'from config import NEXUS_CONFIG'),
    ('utils.logger', 'from utils.logger import get_logger'),
    ('core.event_bus', 'from core.event_bus import event_bus'),
    ('core.state_manager', 'from core.state_manager import state_manager'),
    ('core.memory_system', 'from core.memory_system import memory_system'),
    ('llm.llama_interface', 'from llm.llama_interface import llm'),
    ('llm.context_manager', 'from llm.context_manager import context_manager'),
    ('llm.prompt_engine', 'from llm.prompt_engine import prompt_engine'),
    ('llm.groq_interface', 'from llm.groq_interface import groq_interface'),
    ('llm.llm_router', 'from llm.llm_router import llm_router'),
    ('core.groq_context_collector', 'from core.groq_context_collector import groq_context_collector'),
    ('core.nexus_brain', 'from core.nexus_brain import nexus_brain'),
]

print("\n--- CORE MODULE IMPORTS ---")
for name, stmt in core_modules:
    try:
        exec(stmt)
        print(f"  OK   {name}")
    except Exception as e:
        print(f"  FAIL {name}")
        print(f"       {type(e).__name__}: {e}")
        traceback.print_exc(limit=3)

# Phase 2: Subsystem imports
subsystems = [
    ('consciousness', 'from consciousness import consciousness_system'),
    ('emotions', 'from emotions import emotion_system'),
    ('personality', 'from personality import personality_system'),
    ('body', 'from body import computer_body'),
    ('monitoring', 'from monitoring import monitoring_system'),
    ('learning', 'from learning import learning_system'),
    ('self_improvement', 'from self_improvement import self_improvement_system'),
    ('cognition', 'from cognition import CognitionSystem'),
    ('cognition.cognitive_router', 'from cognition.cognitive_router import cognitive_router'),
    ('cognition.world_model', 'from cognition.world_model import world_model'),
    ('core.autonomy_engine', 'from core.autonomy_engine import autonomy_engine'),
    ('core.internet_agent', 'from core.internet_agent import internet_agent'),
    ('core.social_media_agent', 'from core.social_media_agent import SocialMediaAgent'),
    ('core.conscious_core', 'from core.conscious_core import conscious_core'),
    ('core.alive_spark', 'from core.alive_spark import alive_spark'),
    ('core.pc_control_agent', 'from core.pc_control_agent import pc_control_agent'),
    ('core.voice_engine', 'from core.voice_engine import voice_engine'),
    ('consciousness.global_workspace', 'from consciousness.global_workspace import global_workspace'),
]

print("\n--- SUBSYSTEM IMPORTS ---")
for name, stmt in subsystems:
    try:
        exec(stmt)
        print(f"  OK   {name}")
    except Exception as e:
        print(f"  FAIL {name}")
        print(f"       {type(e).__name__}: {e}")

# Phase 3: Test start() methods
print("\n--- START METHOD TESTS ---")
try:
    from core.nexus_brain import nexus_brain as brain
    brain.start()
    print("  OK   nexus_brain.start()")
except Exception as e:
    print(f"  FAIL nexus_brain.start()")
    print(f"       {type(e).__name__}: {e}")
    traceback.print_exc(limit=5)

# Phase 4: Try to stop cleanly
try:
    brain.stop()
except:
    pass

print("\n" + "=" * 60)
print("  DIAGNOSTICS COMPLETE")
print("=" * 60)
