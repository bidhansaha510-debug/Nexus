import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cognition.world_model import world_model, InteractionType, EmotionalOutcome, TaskOutcome

print('=' * 60)
print('  NEXUS WORLD MODEL TEST')
print('=' * 60)

wm = world_model
wm.start()

# Test user reaction pattern
print('\n--- User Reaction Patterns ---')
wm.observe_user_reaction(
    interaction_type=InteractionType.QUESTION,
    response_time=15.0,
    engagement=0.8,
    outcome='satisfied',
    context_tags=['technical', 'python']
)

prediction = wm.predict_user_reaction(InteractionType.QUESTION, ['technical'])
print(f'  Predicted response time: {prediction["predicted_response_time"]:.1f}s')
print(f'  Predicted engagement: {prediction["predicted_engagement"]:.0%}')
print(f'  Confidence: {prediction["confidence"]:.0%}')

# Test emotional response pattern
print('\n--- Emotional Response Patterns ---')
wm.record_emotional_response(
    trigger_type='statement',
    trigger_category='empathy',
    trigger_content='expressed understanding',
    pre_existing_emotion='frustrated',
    emotional_outcome=EmotionalOutcome.TRUSTING,
    intensity=0.7
)

emo_pred = wm.predict_emotional_outcome('statement', 'empathy', 'frustrated')
print(f'  Predicted outcome: {emo_pred["predicted_outcome"]}')
print(f'  Consistency: {emo_pred["consistency"]:.0%}')

# Test resource consequence
print('\n--- Resource Consequences ---')
wm.record_resource_consequence(
    action_type='llm_call',
    action_category='generation',
    cpu_impact=15.0,
    memory_impact=50.0,
    time_cost=2.5,
    llm_tokens=500
)

resource_est = wm.estimate_resource_cost('llm_call', 'generation')
print(f'  Estimated CPU: {resource_est["estimated_cpu_impact"]:.1f}%')
print(f'  Estimated time: {resource_est["estimated_time_cost"]:.1f}s')
print(f'  Impact level: {resource_est["impact_level"]}')

# Test task success probability
print('\n--- Task Success Probability ---')
wm.record_task_outcome(
    task_type='code_generation',
    task_category='technical',
    task_description='Generate Python function',
    outcome=TaskOutcome.SUCCESS,
    complexity=0.6,
    time_taken=10.0,
    user_satisfaction=0.8
)

success_prob = wm.estimate_success_probability('code_generation', 'technical', 0.6)
print(f'  Success probability: {success_prob["success_probability"]:.0%}')
print(f'  Sample size: {success_prob["sample_size"]}')
print(f'  Recommendation: {success_prob["recommendation"]}')

# Test world state
print('\n--- World State ---')
wm.update_world_state(
    user_emotional_state='happy',
    user_engagement_level=0.8,
    current_interaction_type=InteractionType.CASUAL_CHAT
)

env = wm.get_world_state()
print(f'  User emotion: {env.user_emotional_state}')
print(f'  Engagement: {env.user_engagement_level:.0%}')
print(f'  Time of day: {env.time_of_day}')

# Test prompt context
print('\n--- Prompt Context ---')
print(wm.get_prompt_context())

# Stats
print('\n--- Statistics ---')
stats = wm.get_stats()
for key, value in stats.items():
    print(f'  {key}: {value}')

print('\n World Model test complete!')
