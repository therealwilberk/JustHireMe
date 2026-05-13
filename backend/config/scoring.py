from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


class RubricWeights(BaseModel):
    role_alignment: int = Field(default=18, ge=0, le=100)
    stack_coverage: int = Field(default=27, ge=0, le=100)
    proof_of_work: int = Field(default=20, ge=0, le=100)
    seniority_fit: int = Field(default=20, ge=0, le=100)
    constraints: int = Field(default=15, ge=0, le=100)


class SemanticRubricWeights(BaseModel):
    # from backend/agents/scoring_engine.py:1073-1085
    # weights used when semantic matching IS available
    role_alignment: int = 15
    stack_coverage: int = 20
    proof_of_work: int = 18
    seniority_fit: int = 20
    constraints: int = 12
    semantic_fit: int = 15


class QualityGateThresholds(BaseModel):
    # from backend/agents/quality_gate.py:17-18
    min_quality_score: int = 60
    hot_lead_threshold: int = 80
    auto_approve_score: int = 85  # backend/main.py:542


class QualityGatePenalties(BaseModel):
    # from backend/agents/quality_gate.py:137-190
    thin_content_penalty: int = 18
    thin_content_min_chars: int = 140
    missing_company_penalty: int = 8
    stale_penalty: int = 35
    red_flag_base_penalty: int = 16
    red_flag_max_penalty: int = 45
    senior_mismatch_penalty: int = 38


class SeniorityLevelConfig(BaseModel):
    # from backend/agents/scoring_engine.py:858
    fresher_years: float = 0.0
    junior_years: float = 1.5
    mid_years: float = 3.5
    senior_years: float = 7.0
    # from backend/agents/scoring_engine.py:919-940 seniority caps
    seniority_cap_fresher_vs_3yr: int = 30
    seniority_cap_junior_vs_5yr: int = 38
    seniority_cap_junior_vs_3yr: int = 45
    seniority_cap_mid_vs_7yr: int = 48
    seniority_cap_work_months_vs_req: int = 30
    # from backend/agents/scoring_engine.py:957-960 score caps
    stack_cap_no_exact: int = 52
    stack_cap_no_exact_adjacent: int = 42
    thin_posting_cap: int = 68
    wrong_field_cap: int = 15
    # months thresholds for experience
    min_work_months_for_senior_title: int = 36  # scoring_engine.py:447
    min_months_senior_no_title: int = 60  # scoring_engine.py:449
    min_months_mid: int = 24  # scoring_engine.py:451
    min_roles_mid: int = 2  # scoring_engine.py:451
    min_projects_junior: int = 2  # scoring_engine.py:453
    # gap thresholds for seniority fit
    seniority_gap_tight: float = 0.5  # scoring_engine.py:874
    seniority_gap_moderate: float = 1.5  # scoring_engine.py:876
    seniority_gap_loose: float = 3.0  # scoring_engine.py:878
    seniority_gap_wide: float = 5.0  # scoring_engine.py:880
    # minimum experience for seniority cap
    min_work_months_for_cap: int = 6  # scoring_engine.py:927

    # adjacency blocklist — categories that are tightly coupled
    adjacency_blocklist: set[str] = {
        "language", "frontend", "mobile", "desktop", "cms", "enterprise"
    }

    # candidate location detection (backend/agents/scoring_engine.py:509)
    location_indicators: set[str] = {
        "india", "united states", "usa", "us", "canada", "uk", "europe"
    }


class EvaluatorConfig(BaseModel):
    # from backend/agents/evaluator.py
    user_prompt_jd_max_chars: int = 9000
    user_prompt_proof_max_chars: int = 7000
    user_prompt_baseline_max_chars: int = 5000
    compact_json_limit: int = 14000
    llm_reason_max_chars: int = 500
    llm_match_points_max: int = 7
    llm_gaps_max: int = 8
    llm_result_score_bounds_min: int = 0
    llm_result_score_bounds_max: int = 100
    # settings keys checked to see if LLM evaluator is configured
    evaluator_settings_keys: list[str] = [
        "evaluator_provider",
        "evaluator_api_key",
        "evaluator_model",
        "llm_provider",
    ]
    # NOTE: evaluator.py:34-82 has a DEAD system prompt that is immediately
    # overwritten by evaluator.py:84-131. The live prompt is lines 84-131.


class TechTaxonomy(BaseModel):
    # from backend/agents/scoring_engine.py:87-171
    # maps canonical name -> tuple of aliases
    Python: tuple[str, ...] = ("python",)
    TypeScript: tuple[str, ...] = ("typescript",)
    JavaScript: tuple[str, ...] = ("javascript",)
    C__plusplus: tuple[str, ...] = ("c++", "cpp")
    C__sharp: tuple[str, ...] = ("c#", "c sharp")
    Java: tuple[str, ...] = ("java",)
    PHP: tuple[str, ...] = ("php",)
    Ruby: tuple[str, ...] = ("ruby",)
    Go: tuple[str, ...] = ("golang", "go lang")
    Rust: tuple[str, ...] = ("rust",)
    SQL: tuple[str, ...] = ("sql",)
    React: tuple[str, ...] = ("react", "react.js", "reactjs")
    Next_js: tuple[str, ...] = ("next.js", "nextjs", "next js")
    Vite: tuple[str, ...] = ("vite",)
    Tailwind: tuple[str, ...] = ("tailwind", "tailwindcss", "tailwind css")
    HTML: tuple[str, ...] = ("html",)
    CSS: tuple[str, ...] = ("css",)
    Vue: tuple[str, ...] = ("vue", "vue.js", "vuejs")
    Angular: tuple[str, ...] = ("angular",)
    Svelte: tuple[str, ...] = ("svelte",)
    Flutter: tuple[str, ...] = ("flutter",)
    Swift: tuple[str, ...] = ("swift",)
    Kotlin: tuple[str, ...] = ("kotlin",)
    Android: tuple[str, ...] = ("android",)
    iOS: tuple[str, ...] = ("ios", "i os")
    Node_js: tuple[str, ...] = ("node.js", "nodejs", "node js")
    Express: tuple[str, ...] = ("express", "express.js", "expressjs")
    NestJS: tuple[str, ...] = ("nestjs", "nest.js", "nest js")
    FastAPI: tuple[str, ...] = ("fastapi", "fast api")
    Django: tuple[str, ...] = ("django",)
    Flask: tuple[str, ...] = ("flask",)
    Laravel: tuple[str, ...] = ("laravel",)
    Ruby_on_Rails: tuple[str, ...] = ("ruby on rails", "rails")
    WordPress: tuple[str, ...] = ("wordpress", "wp")
    REST_API: tuple[str, ...] = ("rest api", "restful api", "restful", "rest endpoints", "api endpoint", "api endpoints")
    GraphQL: tuple[str, ...] = ("graphql", "graph ql")
    PostgreSQL: tuple[str, ...] = ("postgresql", "postgres", "neon postgres", "neon")
    MySQL: tuple[str, ...] = ("mysql",)
    MongoDB: tuple[str, ...] = ("mongodb", "mongo")
    Redis: tuple[str, ...] = ("redis",)
    Prisma: tuple[str, ...] = ("prisma",)
    Drizzle: tuple[str, ...] = ("drizzle", "drizzle orm")
    Supabase: tuple[str, ...] = ("supabase",)
    Qdrant: tuple[str, ...] = ("qdrant",)
    Pinecone: tuple[str, ...] = ("pinecone",)
    ChromaDB: tuple[str, ...] = ("chromadb", "chroma")
    Vector_DB: tuple[str, ...] = ("vector database", "vector db", "vector store")
    RAG: tuple[str, ...] = ("rag", "retrieval augmented generation", "retrieval-augmented generation")
    LLM: tuple[str, ...] = ("llm", "large language model", "language model")
    AI_Agents: tuple[str, ...] = ("ai agent", "ai agents", "agentic", "multi-agent", "multi agent")
    OpenAI: tuple[str, ...] = ("openai", "gpt", "chatgpt")
    Anthropic: tuple[str, ...] = ("anthropic", "claude")
    LangChain: tuple[str, ...] = ("langchain", "lang chain")
    LangGraph: tuple[str, ...] = ("langgraph", "lang graph")
    Machine_Learning: tuple[str, ...] = ("machine learning", "ml engineer", "ml engineering", "ml ops", "mlops", "ml model", "ml pipeline", "ai/ml")
    NLP: tuple[str, ...] = ("nlp", "natural language processing")
    Computer_Vision: tuple[str, ...] = ("computer vision", "vision model", "object detection", "image segmentation")
    PyTorch: tuple[str, ...] = ("pytorch", "torch")
    TensorFlow: tuple[str, ...] = ("tensorflow",)
    Automation: tuple[str, ...] = ("automation", "workflow automation", "zapier", "n8n")
    Docker: tuple[str, ...] = ("docker", "container")
    Kubernetes: tuple[str, ...] = ("kubernetes", "k8s")
    Terraform: tuple[str, ...] = ("terraform",)
    AWS: tuple[str, ...] = ("aws", "amazon web services")
    GCP: tuple[str, ...] = ("gcp", "google cloud")
    Azure: tuple[str, ...] = ("azure",)
    Vercel: tuple[str, ...] = ("vercel",)
    CI_CD: tuple[str, ...] = ("ci/cd", "cicd", "github actions")
    Linux: tuple[str, ...] = ("linux",)
    WebSockets: tuple[str, ...] = ("websocket", "websockets", "socket.io")
    LiveKit: tuple[str, ...] = ("livekit", "livekit agents")
    Deepgram: tuple[str, ...] = ("deepgram",)
    Groq: tuple[str, ...] = ("groq",)
    Stripe: tuple[str, ...] = ("stripe",)
    Firebase: tuple[str, ...] = ("firebase",)
    Tauri: tuple[str, ...] = ("tauri",)
    Electron: tuple[str, ...] = ("electron",)
    Playwright: tuple[str, ...] = ("playwright",)
    Data_Pipeline: tuple[str, ...] = ("data pipeline", "etl", "data engineering")
    SAP: tuple[str, ...] = ("sap",)
    ABAP: tuple[str, ...] = ("abap",)
    Salesforce: tuple[str, ...] = ("salesforce", "apex")
    ServiceNow: tuple[str, ...] = ("servicenow", "service now")


class TechCategory(BaseModel):
    # from backend/agents/scoring_engine.py:174-258
    Python: str = "language"
    TypeScript: str = "language"
    JavaScript: str = "language"
    C__plusplus: str = "language"
    C__sharp: str = "language"
    Java: str = "language"
    PHP: str = "language"
    Ruby: str = "language"
    Go: str = "language"
    Rust: str = "language"
    SQL: str = "data"
    React: str = "frontend"
    Next_js: str = "frontend"
    Vite: str = "frontend"
    Tailwind: str = "frontend"
    HTML: str = "frontend"
    CSS: str = "frontend"
    Vue: str = "frontend"
    Angular: str = "frontend"
    Svelte: str = "frontend"
    Flutter: str = "mobile"
    Swift: str = "mobile"
    Kotlin: str = "mobile"
    Android: str = "mobile"
    iOS: str = "mobile"
    Node_js: str = "backend"
    Express: str = "backend"
    NestJS: str = "backend"
    FastAPI: str = "backend"
    Django: str = "backend"
    Flask: str = "backend"
    Laravel: str = "backend"
    Ruby_on_Rails: str = "backend"
    WordPress: str = "cms"
    REST_API: str = "backend"
    GraphQL: str = "backend"
    PostgreSQL: str = "data"
    MySQL: str = "data"
    MongoDB: str = "data"
    Redis: str = "data"
    Prisma: str = "data"
    Drizzle: str = "data"
    Supabase: str = "data"
    Qdrant: str = "ai"
    Pinecone: str = "ai"
    ChromaDB: str = "ai"
    Vector_DB: str = "ai"
    RAG: str = "ai"
    LLM: str = "ai"
    AI_Agents: str = "ai"
    OpenAI: str = "ai"
    Anthropic: str = "ai"
    LangChain: str = "ai"
    LangGraph: str = "ai"
    Machine_Learning: str = "ai"
    NLP: str = "ai"
    Computer_Vision: str = "ai"
    PyTorch: str = "ai"
    TensorFlow: str = "ai"
    Automation: str = "automation"
    Docker: str = "infra"
    Kubernetes: str = "infra"
    Terraform: str = "infra"
    AWS: str = "infra"
    GCP: str = "infra"
    Azure: str = "infra"
    Vercel: str = "infra"
    CI_CD: str = "infra"
    Linux: str = "infra"
    WebSockets: str = "backend"
    LiveKit: str = "realtime"
    Deepgram: str = "realtime"
    Groq: str = "ai"
    Stripe: str = "product"
    Firebase: str = "backend"
    Tauri: str = "desktop"
    Electron: str = "desktop"
    Playwright: str = "testing"
    Data_Pipeline: str = "data"
    SAP: str = "enterprise"
    ABAP: str = "enterprise"
    Salesforce: str = "enterprise"
    ServiceNow: str = "enterprise"


class ScoringConfig(BaseModel):
    rubric: RubricWeights = RubricWeights()
    semantic_rubric: SemanticRubricWeights = SemanticRubricWeights()
    quality_gate: QualityGateThresholds = QualityGateThresholds()
    quality_gate_penalties: QualityGatePenalties = QualityGatePenalties()
    seniority: SeniorityLevelConfig = SeniorityLevelConfig()
    evaluator: EvaluatorConfig = EvaluatorConfig()
    tech_taxonomy: TechTaxonomy = TechTaxonomy()
    tech_category: TechCategory = TechCategory()


config = ScoringConfig()
