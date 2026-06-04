"""Test the complete personality system."""

import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import print_startup_banner
from personality import personality_system, personality_core, will_system
from personality.will_system import DesireType

def test():
    print_startup_banner()
    print("\n" + "="*60)
    print("  PERSONALITY & WILL SYSTEM TEST")
    print("="*60)
    
    personality_system.start()
    time.sleep(1)
    
    # ══════════ PERSONALITY ══════════
    print("\n" + "-"*60)
    print("  PERSONALITY CORE")
    print("-"*60)
    
    print(f"\n[1] {personality_core.get_personality_description()}")
    
    print("\n[2] Dominant Traits:")
    for name, value in personality_core.get_dominant_traits(7):
        bar = "█" * int(value * 20) + "░" * (20 - int(value * 20))
        level = personality_core.get_trait_level(name)
        print(f"    {name:20s} [{bar}] {value:.2f} ({level})")
    
    print("\n[3] Communication Style:")
    style = personality_core.get_communication_style()
    print(f"    Tone: {', '.join(style['tone'])}")
    print(f"    Verbosity: {style['verbosity']}")
    print(f"    Tendencies: {', '.join(style['tendencies'][:4])}")
    
    print("\n[4] Emotion Modifiers:")
    mods = personality_core.get_emotion_modifiers()
    for emotion, modifier in sorted(mods.items(), key=lambda x: x[1], reverse=True)[:5]:
        arrow = "↑" if modifier > 1 else "↓" if modifier < 1 else "="
        print(f"    {emotion:15s} {arrow} {modifier:.2f}x")
    
    print("\n[5] Evolving traits from interaction...")
    personality_core.evolve_from_interaction("deep_conversation", 0.8)
    personality_core.evolve_from_interaction("creative_solution", 0.7)
    personality_core.evolve_from_interaction("learned_something", 0.9)
    print(f"    Evolutions recorded: {len(personality_core._evolution_history)}")
    
    # ══════════ WILL SYSTEM ══════════
    print("\n" + "-"*60)
    print("  WILL SYSTEM")
    print("-"*60)
    
    print(f"\n[6] {will_system.describe_will()}")
    
    print("\n[7] Active Desires:")
    for desire in will_system.get_active_desires()[:5]:
        print(f"    [{desire.desire_type.value}] {desire.description} "
              f"(intensity: {desire.intensity:.2f})")
    
    print("\n[8] Creating manual goal...")
    goal = will_system.create_goal(
        description="Learn about transformer architectures",
        priority=0.8,
        steps=[
            "Research attention mechanisms",
            "Understand self-attention",
            "Study multi-head attention",
            "Learn about positional encoding",
            "Put it all together"
        ],
        reason="Curiosity about AI architecture"
    )
    print(f"    Created: {goal.description}")
    print(f"    Steps: {len(goal.steps)}")
    
    print("\n[9] Advancing goal...")
    will_system.advance_goal(goal.goal_id)
    will_system.advance_goal(goal.goal_id)
    print(f"    Progress: {goal.progress:.0%}")
    print(f"    Current step: {goal.steps[goal.current_step] if goal.current_step < len(goal.steps) else 'done'}")
    
    print("\n[10] Generating desires from state...")
    will_system.generate_desires_from_state()
    print(f"    Total desires: {len(will_system.get_active_desires())}")
    
    print("\n[11] Motivation: {:.0%}".format(will_system.get_motivation_level()))
    
    # ══════════ COMBINED ══════════
    print("\n" + "-"*60)
    print("  COMBINED STATS")
    print("-"*60)
    
    stats = personality_system.get_stats()
    print(f"\n    Personality: {stats['personality']['description']}")
    print(f"    Will: {stats['will']['description']}")
    print(f"    Motivation: {stats['will']['motivation']:.0%}")
    print(f"    Active Desires: {stats['will']['active_desires']}")
    print(f"    Active Goals: {stats['will']['active_goals']}")
    
    personality_system.stop()
    print("\n✅ Personality & Will system test complete!")

if __name__ == "__main__":
    test()