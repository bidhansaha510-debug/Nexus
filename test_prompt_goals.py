import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm.prompt_engine import prompt_engine
from personality.goal_hierarchy import goal_hierarchy

def test_isolated():
    goal_hierarchy._bootstrap_defaults()
    goal_context = goal_hierarchy.get_prompt_context()
    
    prompt = prompt_engine.build_system_prompt(goal_context=goal_context)
    
    if "YOUR CURRENT GOALS:" in prompt:
        print("SUCCESS! Built prompt contains goal context.")
        idx = prompt.find("YOUR CURRENT GOALS:")
        print(prompt[idx:idx+400])
    else:
        print("FAILED: Prompt does not contain goal context.")

if __name__ == "__main__":
    test_isolated()
