from pydantic import BaseModel, Field


class HunterConfig(BaseModel):
    # from backend/agents/contact_lookup.py
    api_url: str = "https://api.hunter.io/v2/domain-search"
    default_timeout: int = 12  # contact_lookup.py:82
    limit_per_domain: int = 10  # contact_lookup.py:117
    max_contacts_returned: int = 5  # contact_lookup.py:123


class ProxycurlConfig(BaseModel):
    # from backend/agents/contact_lookup.py
    api_url: str = "https://nubela.co/proxycurl/api/linkedin/profile/resolve"
    auth_header_template: str = "Bearer {key}"


class ATSHosts(BaseModel):
    # from backend/agents/contact_lookup.py:13-23
    hosts: set[str] = {
        "boards.greenhouse.io",
        "jobs.lever.co",
        "jobs.ashbyhq.com",
        "apply.workable.com",
        "wellfound.com",
        "linkedin.com",
        "www.linkedin.com",
        "indeed.com",
        "www.indeed.com",
    }


class ContactPriority(BaseModel):
    # from backend/agents/contact_lookup.py:26-39
    roles: tuple[str, ...] = (
        "founder",
        "co-founder",
        "ceo",
        "cto",
        "head of engineering",
        "vp engineering",
        "engineering manager",
        "hiring manager",
        "recruiter",
        "talent",
        "people",
        "hr",
    )


class ManagerNamePatterns(BaseModel):
    # from backend/agents/contact_lookup.py:127-132
    patterns: tuple[str, ...] = (
        r"hiring manager\s*[:\-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
        r"recruiter\s*[:\-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
        r"contact\s*[:\-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
        r"report(?:s|ing)?\s+to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
    )


class SkillsDetection(BaseModel):
    # from backend/agents/contact_lookup.py:170
    tech_pattern: str = r"\b(?:Python|FastAPI|React|TypeScript|AWS|Docker|Kubernetes|LLM|AI|PostgreSQL|Kafka|CI/CD)\b"
    max_skills_in_email: int = 4  # contact_lookup.py:178


class ContactConfig(BaseModel):
    hunter: HunterConfig = HunterConfig()
    proxycurl: ProxycurlConfig = ProxycurlConfig()
    ats_hosts: ATSHosts = ATSHosts()
    contact_priority: ContactPriority = ContactPriority()
    manager_name_patterns: ManagerNamePatterns = ManagerNamePatterns()
    skills_detection: SkillsDetection = SkillsDetection()


config = ContactConfig()
