from pydantic import BaseModel, Field
from typing import Literal


class PDFColors(BaseModel):
    # from backend/agents/generator.py:795-798
    accent: tuple[int, int, int] = (31, 78, 121)
    ink: tuple[int, int, int] = (28, 31, 35)
    muted: tuple[int, int, int] = (92, 98, 108)
    rule: tuple[int, int, int] = (183, 194, 207)


class PDFSizing(BaseModel):
    # from backend/agents/generator.py
    page_format: Literal["Letter", "A4"] = "Letter"
    base_margin_resume: int = 11  # generator.py:785 (multiplied by scale)
    base_margin_y_resume: int = 10  # generator.py:786
    base_margin_cover: int = 15  # generator.py:977
    min_font_size: float = 6.2  # generator.py:802
    min_line_height: float = 3.0  # generator.py:804
    scale_values: tuple[float, ...] = (1.28, 1.22, 1.16, 1.10, 1.04, 0.98, 0.92, 0.86, 0.80, 0.76)  # generator.py:943
    cover_scale_values: tuple[float, ...] = (1.0, 0.94, 0.88, 0.82, 0.76, 0.70)  # generator.py:1148
    max_spread: float = 2.20  # generator.py:950
    min_page_usage_ratio: float = 0.90  # generator.py:949
    spread_fill_factor: float = 2.2  # generator.py:950
    font_name: str = "Helvetica"
    rule_line_width: float = 0.25  # generator.py:895
    accent_line_width: float = 0.55  # generator.py:928
    accent_line_margin: float = 10.0  # generator.py:929 (multiplied by scale)


class PDFSizes(BaseModel):
    # from backend/agents/generator.py:978-985
    h1_resume: float = 16.0
    h2_resume: float = 10.8
    h3_resume: float = 9.4
    h4_resume: float = 8.8
    body_resume: float = 8.4
    quote_resume: float = 8.0
    h1_cover: float = 15.0
    h2_cover: float = 12.0
    h3_cover: float = 10.5
    h4_cover: float = 10.0
    body_cover: float = 10.0
    quote_cover: float = 9.4
    name_size: float = 19.0  # generator.py:915
    contact_size: float = 7.8  # generator.py:922
    entry_title_size: float = 8.6  # generator.py:872
    bullet_size: float = 7.8  # generator.py:837


class DocumentWordLimits(BaseModel):
    # from backend/agents/generator.py
    resume_target_min: int = 460  # "Target 460-620 words"
    resume_target_max: int = 620
    cover_letter_target_min: int = 150
    cover_letter_target_max: int = 220
    founder_message_max_chars: int = 280
    linkedin_note_max_chars: int = 300
    cold_email_max_chars: int = 600
    cold_email_max_words: int = 150
    project_shortlist_limit: int = 4  # generator.py:85
    project_fallback_limit: int = 3  # generator.py:301
    resume_description_bullets: int = 3  # generator.py:325
    resume_experience_bullets: int = 4  # generator.py:343
    resume_experience_count: int = 3  # generator.py:335
    cert_display_limit: int = 4  # generator.py:351
    achievement_display_limit: int = 4  # generator.py:353
    education_display_limit: int = 3  # generator.py:355
    top_skills_fallback_count: int = 4  # generator.py:239
    top_skills_email_count: int = 3  # generator.py:248
    top_skills_summary_count: int = 5  # generator.py:360
    top_skills_cover_count: int = 5  # generator.py:378
    keyword_coverage_jd_terms: int = 24  # generator.py:502
    keyword_coverage_covered: int = 18  # generator.py:503
    keyword_coverage_missing: int = 12  # generator.py:504
    keyword_coverage_incorporated: int = 18  # generator.py:505


class OutreachDefaults(BaseModel):
    # from backend/agents/generator.py:233-263
    founder_message_title: str = "the role"
    founder_message_company: str = "your company"
    fallback_skills: str = "software engineering"
    fallback_contact_skills: str = "full-stack development"


class AssetsConfig(BaseModel):
    # from backend/agents/generator.py:10-11
    subdirectory: str = "assets"


class GeneratorConfig(BaseModel):
    pdf_colors: PDFColors = PDFColors()
    pdf_sizing: PDFSizing = PDFSizing()
    pdf_sizes: PDFSizes = PDFSizes()
    word_limits: DocumentWordLimits = DocumentWordLimits()
    outreach_defaults: OutreachDefaults = OutreachDefaults()
    assets: AssetsConfig = AssetsConfig()


config = GeneratorConfig()
