"""
NEXUS AI - LLM Package
Local Llama 3 integration via Ollama
"""

from llm.llama_interface import LlamaInterface, LLMResponse, llm
from llm.context_manager import ContextManager, context_manager
from llm.prompt_engine import PromptEngine, prompt_engine

__all__ = [
    'LlamaInterface', 'LLMResponse', 'llm',
    'ContextManager', 'context_manager',
    'PromptEngine', 'prompt_engine'
]