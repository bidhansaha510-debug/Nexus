"""Utility: list all public methods on each cognition engine."""
import sys, os, logging
logging.disable(logging.CRITICAL)  # suppress all logging
sys.path.insert(0, 'd:/NEXUS')
os.environ['NEXUS_QUIET'] = '1'

engine_list = [
    ('emotional_intelligence', 'emotional_intelligence', 'emotional_intelligence'),
    ('wisdom', 'wisdom_engine', 'wisdom_engine'),
    ('constraint_solver', 'constraint_solver', 'constraint_solver'),
    ('moral_imagination', 'moral_imagination', 'moral_imagination'),
    ('working_memory', 'working_memory', 'working_memory'),
    ('conceptual_blending', 'conceptual_blending', 'conceptual_blending'),
    ('perspective_taking', 'perspective_taking', 'perspective_taking'),
    ('transfer_learning', 'transfer_learning', 'transfer_learning'),
    ('error_detection', 'error_detection', 'error_detection'),
    ('curiosity_drive', 'curiosity_drive', 'curiosity_drive'),
    ('humor_intelligence', 'humor_intelligence', 'humor_intelligence'),
    ('musical_cognition', 'musical_cognition', 'musical_cognition'),
    ('visual_imagination', 'visual_imagination', 'visual_imagination'),
    ('attention_control', 'attention_control', 'attention_control'),
    ('negotiation_intelligence', 'negotiation_intelligence', 'negotiation_intelligence'),
    ('adversarial_thinking', 'adversarial_thinking', 'adversarial_thinking'),
    ('cultural_intelligence', 'cultural_intelligence', 'cultural_intelligence'),
    ('information_synthesis', 'information_synthesis', 'information_synthesis'),
    ('analogy_generator', 'analogy_generator', 'analogy_generator'),
    ('emotional_regulation', 'emotional_regulation', 'emotional_regulation'),
    ('social_cognition', 'social_cognition', 'social_cognition'),
    ('self_model', 'self_model', 'self_model'),
    ('dream_engine', 'dream_engine', 'dream_engine'),
    ('causal_reasoning', 'causal_reasoning', 'causal_reasoning'),
    ('decision_theory', 'decision_theory', 'decision_theory'),
    ('ethical_reasoning', 'ethical_reasoning', 'ethical_reasoning'),
    ('planning', 'planning_engine', 'planning_engine'),
    ('theory_of_mind', 'theory_of_mind', 'theory_of_mind'),
    ('spatial_reasoning', 'spatial_reasoning', 'spatial_reasoning'),
    ('temporal_reasoning', 'temporal_reasoning', 'temporal_reasoning'),
    ('probabilistic_reasoning', 'probabilistic_reasoning', 'probabilistic_reasoning'),
    ('logical_reasoning', 'logical_reasoning', 'logical_reasoning'),
    ('common_sense', 'common_sense', 'common_sense'),
    ('systems_thinking', 'systems_thinking', 'systems_thinking'),
    ('narrative_intelligence', 'narrative_intelligence', 'narrative_intelligence'),
    ('dialectical_reasoning', 'dialectical_reasoning', 'dialectical_reasoning'),
    ('intuition', 'intuition_engine', 'intuition_engine'),
    ('knowledge_integration', 'knowledge_integration', 'knowledge_integration'),
    ('cognitive_flexibility', 'cognitive_flexibility', 'cognitive_flexibility'),
    ('hypothesis', 'hypothesis_engine', 'hypothesis_engine'),
    ('linguistic_intelligence', 'linguistic_intelligence', 'linguistic_intelligence'),
    ('counterfactual_reasoning', 'counterfactual_reasoning', 'counterfactual_reasoning'),
    ('philosophical_reasoning', 'philosophical_reasoning', 'philosophical_reasoning'),
    ('debate', 'debate_engine', 'debate_engine'),
    ('game_theory', 'game_theory', 'game_theory'),
    ('analogical_reasoning', 'analogical_reasoning', 'analogical_reasoning'),
]

skip = {'start','stop','get_stats','to_dict','from_dict'}
for facade, mod, var in engine_list:
    try:
        m = __import__(f'cognition.{mod}', fromlist=[var])
        obj = getattr(m, var)
        cls = type(obj)
        methods = sorted([x for x in dir(cls) if not x.startswith('_') and callable(getattr(cls,x,None)) and x not in skip])
        print(f'{facade}: {methods}')
    except Exception as e:
        print(f'{facade}: ERROR:{e}')
