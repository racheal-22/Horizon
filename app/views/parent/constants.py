"""
constants.py
=====================================================================
Central configuration for the AI Career Guidance module.

Keeping every tunable value in one file means thresholds, model
names, and defaults can be adjusted without touching business logic
in ai.py. This is the only file that should need editing if you
want to change the Gemini model, adjust score thresholds, or tweak
cache duration.
=====================================================================
"""

from django.conf import settings

# ---------------------------------------------------------------------------
# Gemini model configuration
# ---------------------------------------------------------------------------
# Falls back to a sane default if not set in Django settings, so the module
# doesn't hard-crash on import in environments where the setting is missing.
GEMINI_MODEL_NAME: str = getattr(settings, "GEMINI_MODEL_NAME", "gemini-3.1-flash-lite-preview")

GEMINI_TEMPERATURE: float = getattr(settings, "GEMINI_TEMPERATURE", 0.6)
GEMINI_MAX_OUTPUT_TOKENS: int = getattr(settings, "GEMINI_MAX_OUTPUT_TOKENS", 3072)
GEMINI_TOP_P: float = getattr(settings, "GEMINI_TOP_P", 0.9)
GEMINI_TOP_K: int = getattr(settings, "GEMINI_TOP_K", 40)

# Gemini request timeout, in seconds. The SDK accepts this via
# http_options when constructing the client/request.
GEMINI_TIMEOUT_SECONDS: int = getattr(settings, "GEMINI_TIMEOUT_SECONDS", 30)

# Number of retry attempts if the Gemini call fails transiently
# (e.g. network blip, 5xx from the API). Kept small — if Gemini is
# genuinely down, we want to fall back quickly, not hang the request.
GEMINI_MAX_RETRIES: int = getattr(settings, "GEMINI_MAX_RETRIES", 2)


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------
# Career guidance is expensive to generate and doesn't need to change
# every page load — a student's profile doesn't shift meaningfully
# within a day. Cache TTL is deliberately generous.
CAREER_GUIDANCE_CACHE_TTL_SECONDS: int = getattr(
    settings, "CAREER_GUIDANCE_CACHE_TTL_SECONDS", 60 * 60 * 24  # 24 hours
)
CACHE_KEY_PREFIX: str = "career_guidance"


# ---------------------------------------------------------------------------
# Academic thresholds
# ---------------------------------------------------------------------------
STRONG_SUBJECT_THRESHOLD: float = 70.0
WEAK_SUBJECT_THRESHOLD: float = 50.0
GOOD_ATTENDANCE_THRESHOLD: float = 85.0
LOW_ATTENDANCE_THRESHOLD: float = 75.0

# Minimum five-year growth (percentage points) to be considered a
# "meaningful" improvement, as opposed to noise between exams.
MEANINGFUL_GROWTH_THRESHOLD: float = 5.0


# ---------------------------------------------------------------------------
# Defaults for missing/null data
# ---------------------------------------------------------------------------
# Centralised so every builder function uses identical fallback text
# instead of each inventing its own "N/A"-style string.
DEFAULT_STUDENT_NAME: str = "the student"
DEFAULT_UNKNOWN_VALUE: str = "Not available"
DEFAULT_LEARNING_STYLE: str = "Balanced"
DEFAULT_CAREER_CATEGORY: str = "General"

MAX_CAREER_RECOMMENDATIONS: int = 5
MAX_FUTURE_SKILLS: int = 5
MAX_ROADMAP_STEPS: int = 6


# ---------------------------------------------------------------------------
# Response source labels (used in AIResponse.source)
# ---------------------------------------------------------------------------
SOURCE_GEMINI: str = "gemini"
SOURCE_FALLBACK: str = "fallback"
SOURCE_CACHE: str = "cache"