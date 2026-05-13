from pydantic import BaseModel, Field
from typing import Literal


class LLMProviderDefaults(BaseModel):
    # from backend/llm.py:56-73
    anthropic: str = "claude-sonnet-4-6"
    gemini: str = "gemini-2.5-flash"
    groq: str = "llama-3.3-70b-versatile"
    nvidia: str = "z-ai/glm-5.1"
    openai: str = "gpt-4o-mini"
    deepseek: str = "deepseek-chat"
    xai: str = "grok-4"
    kimi: str = "kimi-k2-turbo-preview"
    mistral: str = "mistral-large-latest"
    openrouter: str = "openrouter/auto"
    together: str = "openai/gpt-oss-120b"
    fireworks: str = "accounts/fireworks/models/llama-v3p1-70b-instruct"
    cerebras: str = "llama-3.3-70b"
    perplexity: str = "sonar"
    huggingface: str = "openai/gpt-oss-120b"
    custom: str = "model-id"
    ollama: str = "llama3"


class LLMProviderEndpoints(BaseModel):
    # from backend/llm.py:75-85 (OpenAI-compatible base URLs)
    xai: str = "https://api.x.ai/v1"
    kimi: str = "https://api.moonshot.ai/v1"
    mistral: str = "https://api.mistral.ai/v1"
    openrouter: str = "https://openrouter.ai/api/v1"
    together: str = "https://api.together.xyz/v1"
    fireworks: str = "https://api.fireworks.ai/inference/v1"
    cerebras: str = "https://api.cerebras.ai/v1"
    perplexity: str = "https://api.perplexity.ai/v1"
    huggingface: str = "https://router.huggingface.co/v1"


class LLMKeyNames(BaseModel):
    # from backend/llm.py:35-52 — maps provider id to env var name
    anthropic: str = "ANTHROPIC_API_KEY"
    gemini: str = "GEMINI_API_KEY"
    groq: str = "GROQ_API_KEY"
    nvidia: str = "NVIDIA_API_KEY"
    openai: str = "OPENAI_API_KEY"
    deepseek: str = "DEEPSEEK_API_KEY"
    xai: str = "XAI_API_KEY"
    kimi: str = "MOONSHOT_API_KEY"
    mistral: str = "MISTRAL_API_KEY"
    openrouter: str = "OPENROUTER_API_KEY"
    together: str = "TOGETHER_API_KEY"
    fireworks: str = "FIREWORKS_API_KEY"
    cerebras: str = "CEREBRAS_API_KEY"
    perplexity: str = "PERPLEXITY_API_KEY"
    huggingface: str = "HF_TOKEN"
    custom: str = "OPENAI_COMPAT_API_KEY"


class LLMProviderSpecific(BaseModel):
    # from backend/llm.py
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"  # llm.py:146
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"  # llm.py:157
    groq_base_url: str = "https://api.groq.com/openai/v1"  # llm.py:201
    deepseek_base_url: str = "https://api.deepseek.com"  # llm.py:255
    anthropic_api_url: str = "https://api.anthropic.com/v1/messages"  # main.py:1380
    anthropic_timeout: float = 120.0  # llm.py:186 (fallback from main.py:1376 uses 5.0 for probe)
    anthropic_api_version: str = "2023-06-01"  # main.py:1383
    anthropic_probe_model: str = "claude-haiku-4-5-20251001"  # main.py:1387
    openai_probe_url: str = "https://api.openai.com/v1/models"  # main.py:1395
    groq_probe_url: str = "https://api.groq.com/openai/v1/models"  # main.py:1401
    gemini_probe_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/models"  # main.py:1407
    gemini_env_key_fallback: str = "GOOGLE_API_KEY"  # llm.py:122
    custom_base_url_setting_key: str = "custom_base_url"  # llm.py:93
    custom_base_url_env_fallback: str = "OPENAI_COMPAT_BASE_URL"  # llm.py:94
    custom_base_url_hard_fallback: str = "https://api.openai.com/v1"  # llm.py:95
    ollama_default_url: str = "http://localhost:11434/v1"  # llm.py:292


class LLMConfig(BaseModel):
    # from backend/llm.py:12
    timeout_seconds: float = Field(default=300.0, ge=1.0, le=3600.0)
    connect_timeout_seconds: float = Field(default=10.0, ge=1.0, le=120.0)
    max_tokens: int = Field(default=4096, ge=64, le=131072)
    nvidia_max_tokens: int = Field(default=16384, ge=64, le=131072)
    default_provider: str = "ollama"

    default_models: LLMProviderDefaults = LLMProviderDefaults()
    compat_endpoints: LLMProviderEndpoints = LLMProviderEndpoints()
    env_key_names: LLMKeyNames = LLMKeyNames()
    provider_specific: LLMProviderSpecific = LLMProviderSpecific()


config = LLMConfig()
