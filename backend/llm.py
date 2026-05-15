import os
import httpx
import anthropic
import instructor
from openai import OpenAI
from pydantic import BaseModel
from config import settings
from db.client import get_setting
from logger import get_logger

_log = get_logger(__name__)

_TIMEOUT = httpx.Timeout(300.0, connect=10.0)

# Maps provider id → settings key holding the global API key
_KEY_NAMES: dict[str, str] = settings.llm.settings_key_names.model_dump()

# Maps provider id → environment variable fallback
_ENV_NAMES: dict[str, str] = settings.llm.env_key_names.model_dump()

# Default model per provider (used when no step/global model is set)
_DEFAULT_MODELS: dict[str, str] = settings.llm.default_models.model_dump()

_OPENAI_COMPAT_BASE_URLS: dict[str, str] = settings.llm.compat_endpoints.model_dump()

_OPENAI_COMPAT_PROVIDERS = set(_OPENAI_COMPAT_BASE_URLS) | {"custom"}


def _provider_base_url(provider: str) -> str:
    p = settings.llm.provider_specific
    if provider == "custom":
        return (
            get_setting(p.custom_base_url_setting_key, "")
            or os.environ.get(p.custom_base_url_env_fallback, "")
            or p.custom_base_url_hard_fallback
        )
    return _OPENAI_COMPAT_BASE_URLS[provider]


def _resolve(step: str | None = None) -> tuple[str, str, str]:
    """
    Resolve (provider, api_key, model) for a given pipeline step.

    Priority order:
      1. Step-specific setting  ({step}_provider / {step}_api_key / {step}_model)
      2. Global setting         (llm_provider / provider key / nvidia_model etc.)
      3. Environment variable   (ANTHROPIC_API_KEY etc.)
      4. Hardcoded defaults
    """
    sp = get_setting(f"{step}_provider", "") if step else ""
    sk = get_setting(f"{step}_api_key",  "") if step else ""
    sm = get_setting(f"{step}_model",    "") if step else ""

    p = sp or get_setting("llm_provider", "ollama")

    # API key: step-specific > resolve_secret (env > SQLite fallback)
    if sk:
        k = sk
    else:
        from config.secrets import resolve_secret
        env_name = _ENV_NAMES.get(p, "")
        settings_key = _KEY_NAMES.get(p, "")
        k = resolve_secret(env_name, settings_key)
        if not k and p == "gemini":
            k = resolve_secret(settings.llm.provider_specific.gemini_env_key_fallback, None)
        k = k or ""

    # Model: step-specific > provider-level setting > default
    if sm:
        model = sm
    elif p in _DEFAULT_MODELS:
        model = get_setting(f"{p}_model", _DEFAULT_MODELS[p])
    else:
        model = _DEFAULT_MODELS.get(p, "llama3")

    if step:
        _log.debug("step=%s → provider=%s model=%s", step, p, model)

    return p, k, model


def resolve_config(step: str | None = None) -> tuple[str, str, str]:
    """Public resolver for agents that need provider-specific request shapes."""
    return _resolve(step)


def _client_nvidia(k: str):
    return instructor.from_openai(
        OpenAI(
            base_url=settings.llm.provider_specific.nvidia_base_url,
            api_key=k,
            timeout=_TIMEOUT,
            max_retries=0,
        ),
        mode=instructor.Mode.JSON,
    )


def _client_gemini(k: str):
    return OpenAI(
        base_url=settings.llm.provider_specific.gemini_base_url,
        api_key=k,
        timeout=_TIMEOUT,
        max_retries=0,
    )


def _client_openai_compat(provider: str, key: str):
    return OpenAI(
        base_url=_provider_base_url(provider),
        api_key=key,
        timeout=_TIMEOUT,
        max_retries=0,
    )


def call_llm(s: str, u: str, m: type[BaseModel], step: str | None = None):
    """
    Call LLM with structured output.

    Pass `step` (e.g. "evaluator", "scout", "ingestor") to use that step's
    per-step provider/key/model settings. Omit for global defaults.
    """
    p, k, model = _resolve(step)

    if p == "anthropic":
        if not k:
            _log.warning("anthropic — no key (step=%s) — falling back", step)
            return _parse_fallback(u, m)
        c = anthropic.Anthropic(api_key=k, timeout=120.0)
        r = c.messages.parse(
            model=model,
            max_tokens=4096,
            system=s,
            messages=[{"role": "user", "content": u}],
            output_format=m,
        )
        return r.parsed_output

    elif p == "groq":
        if not k:
            _log.warning("groq — no key (step=%s) — falling back", step)
            return _parse_fallback(u, m)
        c = instructor.from_openai(
            OpenAI(base_url=settings.llm.provider_specific.groq_base_url, api_key=k,
                   timeout=_TIMEOUT, max_retries=0)
        )
        return c.chat.completions.create(
            model=model,
            response_model=m,
            max_retries=1,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )

    elif p == "gemini":
        if not k:
            _log.warning("gemini: no key (step=%s); falling back", step)
            return _parse_fallback(u, m)
        c = instructor.from_openai(_client_gemini(k), mode=instructor.Mode.JSON)
        return c.chat.completions.create(
            model=model,
            response_model=m,
            max_retries=1,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )

    elif p == "nvidia":
        if not k:
            _log.warning("nvidia — no key (step=%s) — falling back", step)
            return _parse_fallback(u, m)
        c = _client_nvidia(k)
        return c.chat.completions.create(
            model=model,
            response_model=m,
            max_retries=1,
            max_tokens=16384,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )

    elif p == "openai":
        if not k:
            _log.warning("openai — no key (step=%s)", step)
            return _parse_fallback(u, m)
        c = instructor.from_openai(OpenAI(api_key=k, timeout=_TIMEOUT))
        return c.chat.completions.create(
            model=model,
            response_model=m,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )

    elif p == "deepseek":
        if not k:
            _log.warning("deepseek — no key (step=%s)", step)
            return _parse_fallback(u, m)
        # deepseek-reasoner does not support tool_choice — use JSON mode instead
        mode = instructor.Mode.JSON if "reasoner" in model else instructor.Mode.TOOLS
        c = instructor.from_openai(
             OpenAI(base_url=settings.llm.provider_specific.deepseek_base_url, api_key=k, timeout=_TIMEOUT),
            mode=mode,
        )
        return c.chat.completions.create(
            model=model,
            response_model=m,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )

    elif p in _OPENAI_COMPAT_PROVIDERS:
        if not k:
            _log.warning("%s — no key (step=%s)", p, step)
            return _parse_fallback(u, m)
        if p == "perplexity":
            schema = m.model_json_schema()
            raw = call_raw(
                s + "\nReturn only valid JSON matching this schema:\n" + str(schema),
                u,
                step=step,
            )
            try:
                return m.model_validate_json(raw)
            except Exception:
                _log.warning("perplexity structured parse failed (step=%s)", step)
                return _parse_fallback(u, m)
        c = instructor.from_openai(
            _client_openai_compat(p, k),
            mode=instructor.Mode.JSON,
        )
        return c.chat.completions.create(
            model=model,
            response_model=m,
            max_retries=1,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )

    else:  # ollama / default
        b = get_setting("ollama_url", settings.llm.provider_specific.ollama_default_url)
        _log.info("ollama at %s model=%s (step=%s)", b, model, step)
        c = instructor.from_openai(
            OpenAI(base_url=b, api_key="ollama", timeout=_TIMEOUT, max_retries=0)
        )
        return c.chat.completions.create(
            model=model,
            response_model=m,
            max_retries=1,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )


def call_raw(s: str, u: str, step: str | None = None) -> str:
    """
    Call LLM for free-form text output.

    Pass `step` (e.g. "generator") to use that step's per-step settings.
    """
    p, k, model = _resolve(step)

    if p == "anthropic":
        if not k:
            return ""
        c = anthropic.Anthropic(api_key=k, timeout=120.0)
        r = c.messages.create(
            model=model,
            max_tokens=4096,
            system=s,
            messages=[{"role": "user", "content": u}],
        )
        return r.content[0].text

    elif p == "groq":
        if not k:
            return ""
        c = OpenAI(base_url=settings.llm.provider_specific.groq_base_url, api_key=k,
                   timeout=_TIMEOUT, max_retries=0)
        r = c.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )
        return r.choices[0].message.content or ""

    elif p == "gemini":
        if not k:
            return ""
        c = _client_gemini(k)
        r = c.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )
        return r.choices[0].message.content or ""

    elif p == "nvidia":
        if not k:
            return ""
        c = OpenAI(base_url=settings.llm.provider_specific.nvidia_base_url, api_key=k,
                   timeout=_TIMEOUT, max_retries=0)
        r = c.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
            max_tokens=16384,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        return r.choices[0].message.content or ""

    elif p == "openai":
        if not k:
            return ""
        c = OpenAI(api_key=k, timeout=_TIMEOUT)
        r = c.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )
        return r.choices[0].message.content or ""

    elif p == "deepseek":
        if not k:
            return ""
        c = OpenAI(base_url=settings.llm.provider_specific.deepseek_base_url, api_key=k, timeout=_TIMEOUT)
        r = c.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )
        return r.choices[0].message.content or ""

    elif p in _OPENAI_COMPAT_PROVIDERS:
        if not k:
            return ""
        c = _client_openai_compat(p, k)
        if p == "perplexity":
            r = c.responses.create(
                model=model,
                instructions=s,
                input=u,
            )
            return getattr(r, "output_text", "") or ""
        r = c.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )
        return r.choices[0].message.content or ""

    else:  # ollama
        b = get_setting("ollama_url", settings.llm.provider_specific.ollama_default_url)
        c = OpenAI(base_url=b, api_key="ollama", timeout=_TIMEOUT, max_retries=0)
        r = c.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )
        return r.choices[0].message.content or ""


def _parse_fallback(u: str, m: type[BaseModel]):
    """Minimal local fallback — no LLM, returns empty structured output."""
    try:
        return m()
    except Exception:
        return m.model_construct()
