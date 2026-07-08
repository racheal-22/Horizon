"""
ai.py
=====================================================================
AI Career Guidance engine for Horizon Student Analytics.

This module is intentionally database-free. Every function here
takes already-computed dashboard data (the same dicts your
dashboard.py already builds for the Overview/Subjects/etc. tabs) and
either:

    (a) shapes that data into a compact context for Gemini, or
    (b) calls Gemini and parses/validates its response, or
    (c) produces a rule-based fallback if Gemini is unavailable.

Nothing in this file touches models.py, querysets, or the ORM. If you
need to change what data feeds career guidance, do it in dashboard.py
and pass the result in — do not import models here.

Public entry point for views/dashboard.py:
    generate_career_guidance(context: CareerContext) -> AIResponse
=====================================================================
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache

from google import genai
from google.genai import types as genai_types

from . import career_mapping as cm
from . import prompts
from .constants import (
    CACHE_KEY_PREFIX,
    CAREER_GUIDANCE_CACHE_TTL_SECONDS,
    DEFAULT_CAREER_CATEGORY,
    DEFAULT_LEARNING_STYLE,
    DEFAULT_STUDENT_NAME,
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL_NAME,
    GEMINI_TEMPERATURE,
    GEMINI_TIMEOUT_SECONDS,
    GEMINI_TOP_K,
    GEMINI_TOP_P,
    GOOD_ATTENDANCE_THRESHOLD,
    MAX_CAREER_RECOMMENDATIONS,
    MAX_FUTURE_SKILLS,
    MAX_ROADMAP_STEPS,
    MEANINGFUL_GROWTH_THRESHOLD,
    SOURCE_CACHE,
    SOURCE_FALLBACK,
    SOURCE_GEMINI,
    STRONG_SUBJECT_THRESHOLD,
    WEAK_SUBJECT_THRESHOLD,
)
from .schemas import AIResponse, CareerContext, CareerRecommendation, StudentProfile

logger = logging.getLogger(__name__)


# =============================================================================
# GEMINI CLIENT — lazy singleton
# =============================================================================
_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """
    Returns a module-level singleton Gemini client, created on first use.

    Lazy initialization matters here: importing this module (e.g. during
    Django's app-loading / migrations / tests) should never require a
    valid API key or network access. The client is only actually created
    the first time generation is attempted.
    """
    global _client
    if _client is None:
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            # Fail loudly here rather than passing None into the SDK,
            # which would produce a much less obvious error later.
            raise RuntimeError(
                "GEMINI_API_KEY is not configured in Django settings. "
                "Set settings.GEMINI_API_KEY to enable AI career guidance."
            )
        _client = genai.Client(api_key=api_key)
    return _client


# =============================================================================
# CACHING
# =============================================================================
def _hash_context(context: CareerContext) -> str:
    """
    Produces a stable hash of the context so identical student data
    (same scores, same achievements) reuses a cached response instead
    of calling Gemini again. Uses sort_keys=True so dict key ordering
    never changes the hash.
    """
    serialized = json.dumps(context.to_dict(), sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _cache_key(context_hash: str) -> str:
    return f"{CACHE_KEY_PREFIX}:{context_hash}"


# =============================================================================
# CONTEXT BUILDERS
# Each function below takes one or more raw dashboard.py outputs and
# returns a small, AI-friendly dict/StudentProfile. None of these query
# the database — every input is assumed to already be computed.
# =============================================================================
def build_student_profile(
    child: Dict[str, Any],
    summary: Dict[str, Any],
    academic_summary: Dict[str, Any],
    attendance_data: Dict[str, Any],
    achievements: Optional[List[Dict[str, Any]]] = None,
    project_data: Optional[Dict[str, Any]] = None,
    remedial_data: Optional[Dict[str, Any]] = None,
) -> StudentProfile:
    """
    Flattens child/summary/academic_summary/attendance_data into a
    single StudentProfile. Every field is defended against missing
    keys — dashboard outputs may legitimately omit fields for a
    student with incomplete data (e.g. no exams recorded yet).
    """
    achievements = achievements or []
    project_data = project_data or {}
    remedial_data = remedial_data or {}

    first_name = (child or {}).get("first_name") or ""
    last_name = (child or {}).get("last_name") or ""
    name = f"{first_name} {last_name}".strip() or DEFAULT_STUDENT_NAME

    top_subject = (academic_summary or {}).get("top_subject") or {}
    weak_subject = (academic_summary or {}).get("weak_subject") or {}

    return StudentProfile(
        name=name,
        std=str((summary or {}).get("std", "")),
        division=str((summary or {}).get("division", "")),
        overall_score=_safe_float((summary or {}).get("overall_score")),
        attendance_percentage=_safe_float((attendance_data or {}).get("days_present")),
        top_subjects=[top_subject["name"]] if top_subject.get("name") else [],
        weak_subjects=[weak_subject["name"]] if weak_subject.get("name") else [],
        learning_style=DEFAULT_LEARNING_STYLE,
        interests=[],  # populated externally if/when the frontend collects interests
        strengths=_derive_strengths(academic_summary, achievements),
        has_remedial_support=bool(remedial_data.get("is_remedial")),
        achievement_count=len(achievements),
        project_count=int(project_data.get("project_count") or 0),
    )


def build_learning_profile(
    learning_rhythm: Dict[str, Any],
    library_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Summarizes reading habits and learning-rhythm signals into a
    compact dict. Kept as a plain dict (rather than a dataclass)
    because its shape is intentionally loose — different dashboards
    may attach different rhythm signals over time.
    """
    library_data = library_data or {}
    learning_rhythm = learning_rhythm or {}

    return {
        "is_active_reader": bool(library_data.get("is_reader")),
        "books_read": int(library_data.get("total_books") or 0),
        "favorite_genre": library_data.get("favorite_type") or None,
        "rhythm_strengths": learning_rhythm.get("strengths") or [],
        "rhythm_concerns": learning_rhythm.get("concerns") or [],
    }


def build_strength_analysis(
    academic_summary: Dict[str, Any],
    subject_growth_journey: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Distills the growth-journey subject list into "strong", "weak",
    and "improving" buckets using the thresholds in constants.py —
    this is the same logic that colors the Scholastic Journey bars,
    just repurposed for the AI's benefit.
    """
    subject_growth_journey = subject_growth_journey or {}
    subjects = subject_growth_journey.get("subjects") or []

    strong = [s["subject"] for s in subjects if _safe_float(s.get("current_score")) >= STRONG_SUBJECT_THRESHOLD]
    weak = [s["subject"] for s in subjects if _safe_float(s.get("current_score")) < WEAK_SUBJECT_THRESHOLD]
    improving = [
        s["subject"] for s in subjects
        if _safe_float(s.get("five_year_growth")) >= MEANINGFUL_GROWTH_THRESHOLD
    ]

    top_improving = subject_growth_journey.get("top_improving_subject") or {}
    top_declining = subject_growth_journey.get("top_declining_subject") or {}

    return {
        "strong_subjects": strong,
        "weak_subjects": weak,
        "improving_subjects": improving,
        "most_improved_subject": top_improving.get("subject"),
        "most_declining_subject": top_declining.get("subject"),
        "top_subject": (academic_summary or {}).get("top_subject", {}).get("name"),
        "weak_subject": (academic_summary or {}).get("weak_subject", {}).get("name"),
    }


def build_skill_analysis(
    achievements: List[Dict[str, Any]],
    project_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Converts achievement categories into demonstrated skills using
    career_mapping.ACHIEVEMENT_SKILL_MAP, and notes project
    involvement as a signal of applied/practical skill.
    """
    achievements = achievements or []
    project_data = project_data or {}

    demonstrated_skills: List[str] = []
    for achievement in achievements:
        category = achievement.get("category", "")
        demonstrated_skills.extend(cm.get_skills_for_achievement_category(category))

    # De-duplicate while preserving order (stable, human-readable output)
    seen = set()
    unique_skills = []
    for skill in demonstrated_skills:
        if skill not in seen:
            seen.add(skill)
            unique_skills.append(skill)

    return {
        "demonstrated_skills": unique_skills,
        "has_project_experience": int(project_data.get("project_count") or 0) > 0,
        "project_types": [p.get("type") for p in (project_data.get("projects") or []) if p.get("type")],
    }


def build_subject_analysis(subject_growth_journey: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maps each subject the student is strong in to candidate careers,
    using career_mapping.SUBJECT_CAREER_MAP. This gives the AI (and
    the fallback) a concrete starting list of career titles grounded
    in actual subject performance, rather than inventing careers from
    nothing.
    """
    subject_growth_journey = subject_growth_journey or {}
    subjects = subject_growth_journey.get("subjects") or []

    subject_career_candidates: Dict[str, List[str]] = {}
    for s in subjects:
        subject_name = s.get("subject")
        if not subject_name:
            continue
        if _safe_float(s.get("current_score")) >= STRONG_SUBJECT_THRESHOLD:
            subject_career_candidates[subject_name] = cm.get_careers_for_subject(subject_name)

    return {"subject_career_candidates": subject_career_candidates}


def build_career_context(
    child: Dict[str, Any],
    summary: Dict[str, Any],
    academic_summary: Dict[str, Any],
    subject_growth_journey: Dict[str, Any],
    learning_rhythm: Dict[str, Any],
    library_data: Dict[str, Any],
    project_data: Dict[str, Any],
    achievements: List[Dict[str, Any]],
    remedial_data: Dict[str, Any],
    attendance_data: Dict[str, Any],
    behaviour_data: Optional[Dict[str, Any]] = None,
) -> CareerContext:
    """
    The single composition function that assembles a CareerContext
    from every dashboard.py output. This is the only function views/
    dashboard.py should need to call before generate_career_guidance().

    All parameters mirror the dashboard outputs listed in the module
    docstring. `behaviour_data` is optional and may be None.
    """
    student_profile = build_student_profile(
        child=child,
        summary=summary,
        academic_summary=academic_summary,
        attendance_data=attendance_data,
        achievements=achievements,
        project_data=project_data,
        remedial_data=remedial_data,
    )

    behaviour_notes = None
    if behaviour_data:
        behaviour_notes = behaviour_data.get("notes") or behaviour_data.get("summary")

    return CareerContext(
        student_profile=student_profile,
        learning_profile=build_learning_profile(learning_rhythm, library_data),
        strength_analysis=build_strength_analysis(academic_summary, subject_growth_journey),
        skill_analysis=build_skill_analysis(achievements, project_data),
        subject_analysis=build_subject_analysis(subject_growth_journey),
        raw_achievements=achievements or [],
        raw_projects=(project_data or {}).get("projects") or [],
        behaviour_notes=behaviour_notes,
    )


# =============================================================================
# GENERATION — the main public entry point
# =============================================================================
def generate_career_guidance(context: CareerContext, force_refresh: bool = False) -> AIResponse:
    """
    Generates career guidance for a student, using Gemini when
    available and falling back to rule-based guidance otherwise.

    Args:
        context: A CareerContext built via build_career_context().
        force_refresh: If True, bypasses the cache and calls Gemini
            again even if a cached response exists for this context.

    Returns:
        An AIResponse — always populated, never raises. Any failure
        (missing API key, network error, malformed AI response) is
        caught internally and results in a fallback_response() instead
        of an exception, so a broken AI integration never breaks the
        dashboard page around it.
    """
    context_hash = _hash_context(context)
    cache_key = _cache_key(context_hash)

    if not force_refresh:
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("career_guidance cache hit for %s", context_hash[:12])
            cached["source"] = SOURCE_CACHE
            return _dict_to_ai_response(cached)

    try:
        response = _call_gemini(context)
        cache.set(cache_key, response.to_dict(), CAREER_GUIDANCE_CACHE_TTL_SECONDS)
        return response
    except Exception as exc:  # noqa: BLE001 — intentionally broad, see module docstring
        logger.warning(
            "Gemini career guidance generation failed, using fallback: %s",
            exc,
            exc_info=True,
        )
        return fallback_response(context, reason=str(exc))


def _call_gemini(context: CareerContext) -> AIResponse:
    """
    Builds the prompt, calls Gemini with retry, and parses the result.
    Raises on failure — callers are expected to catch and fall back.
    """
    client = _get_client()

    prompt = prompts.build_career_guidance_prompt(
        student_profile_json=json.dumps(context.student_profile.to_dict(), default=str),
        learning_profile_json=json.dumps(context.learning_profile, default=str),
        strength_analysis_json=json.dumps(context.strength_analysis, default=str),
        skill_analysis_json=json.dumps(context.skill_analysis, default=str),
        subject_analysis_json=json.dumps(context.subject_analysis, default=str),
        additional_context_json=json.dumps(
            {
                "achievements": context.raw_achievements,
                "projects": context.raw_projects,
                "behaviour_notes": context.behaviour_notes,
            },
            default=str,
        ),
        max_recommendations=MAX_CAREER_RECOMMENDATIONS,
        max_future_skills=MAX_FUTURE_SKILLS,
        max_roadmap_steps=MAX_ROADMAP_STEPS,
    )

    full_prompt = f"{prompts.SYSTEM_PROMPT}\n\n{prompt}"

    generation_config = genai_types.GenerateContentConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
        top_p=GEMINI_TOP_P,
        top_k=GEMINI_TOP_K,
        response_mime_type="application/json",
    )

    last_error: Optional[Exception] = None
    for attempt in range(1, GEMINI_MAX_RETRIES + 1):
        try:
            raw_response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=full_prompt,
                config=generation_config,
            )
            raw_text = _extract_text(raw_response)
            return parse_ai_response(raw_text, context)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.info("Gemini attempt %s/%s failed: %s", attempt, GEMINI_MAX_RETRIES, exc)
            if attempt < GEMINI_MAX_RETRIES:
                time.sleep(min(2 ** attempt, GEMINI_TIMEOUT_SECONDS))

    # All retries exhausted — re-raise the last error so the caller
    # (generate_career_guidance) catches it and falls back.
    assert last_error is not None
    raise last_error


def _extract_text(raw_response: Any) -> str:
    """
    Pulls the text payload out of a Gemini response object. Isolated
    into its own function because the SDK's response shape is the
    most likely thing to change between SDK versions — if it does,
    only this function needs updating.
    """
    text = getattr(raw_response, "text", None)
    if not text:
        raise ValueError("Gemini response contained no text content.")
    return text


# =============================================================================
# PARSING
# =============================================================================
def parse_ai_response(raw_text: str, context: CareerContext) -> AIResponse:
    """
    Parses Gemini's raw JSON text into a validated AIResponse.

    Defensive by design: Gemini is asked to return pure JSON, but
    models occasionally wrap output in markdown code fences or add
    stray whitespace — both are stripped before parsing. Any field
    missing from the parsed JSON falls back to an empty/default value
    rather than raising, since a partially-useful AI response is
    better than none. A completely unparseable response raises
    ValueError, which the caller treats as a Gemini failure and
    triggers fallback_response().
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        # Strip ```json ... ``` or ``` ... ``` wrapping, if present.
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Gemini response JSON was not an object at the top level.")

    recommendations: List[CareerRecommendation] = []
    for item in data.get("career_recommendations", []) or []:
        if not isinstance(item, dict) or not item.get("title"):
            continue  # skip malformed entries rather than failing the whole response
        recommendations.append(
            CareerRecommendation(
                title=str(item.get("title", "")),
                category=str(item.get("category") or DEFAULT_CAREER_CATEGORY),
                match_score=_safe_int(item.get("match_score"), default=50),
                reason=str(item.get("reason") or ""),
                required_skills=[str(s) for s in (item.get("required_skills") or [])],
                roadmap=[str(s) for s in (item.get("roadmap") or [])],
            )
        )

    if not recommendations:
        raise ValueError("Gemini response contained no usable career recommendations.")

    return AIResponse(
        success=True,
        source=SOURCE_GEMINI,
        student_name=context.student_profile.name,
        summary=str(data.get("summary") or ""),
        career_recommendations=recommendations[:MAX_CAREER_RECOMMENDATIONS],
        parent_guidance=[str(t) for t in (data.get("parent_guidance") or [])],
        future_skills=[
            {
                "name": str(fs.get("name", "")),
                "description": str(fs.get("description", "")),
                "why_it_matters": str(fs.get("why_it_matters", "")),
            }
            for fs in (data.get("future_skills") or [])
            if isinstance(fs, dict)
        ][:MAX_FUTURE_SKILLS],
        learning_roadmap=[str(s) for s in (data.get("learning_roadmap") or [])][:MAX_ROADMAP_STEPS],
    )


def _dict_to_ai_response(data: Dict[str, Any]) -> AIResponse:
    """Reconstructs an AIResponse from its cached dict form (cache.get)."""
    recommendations = [
        CareerRecommendation(**rec) for rec in data.get("career_recommendations", [])
    ]
    return AIResponse(
        success=data.get("success", True),
        source=data.get("source", SOURCE_CACHE),
        student_name=data.get("student_name", DEFAULT_STUDENT_NAME),
        summary=data.get("summary", ""),
        career_recommendations=recommendations,
        parent_guidance=data.get("parent_guidance", []),
        future_skills=data.get("future_skills", []),
        learning_roadmap=data.get("learning_roadmap", []),
        generated_at=data.get("generated_at", ""),
        error_message=data.get("error_message"),
    )


# =============================================================================
# FALLBACK — rule-based guidance, no AI call at all
# =============================================================================
def fallback_response(context: CareerContext, reason: str = "") -> AIResponse:
    """
    Produces a fully rule-based AIResponse using only career_mapping.py
    data — no network call, cannot fail due to an external service.
    Used whenever Gemini is unreachable, unconfigured, or returns an
    unparseable response.

    The output shape is identical to a Gemini-sourced AIResponse, so
    templates never need to special-case `source == "fallback"`.
    """
    profile = context.student_profile
    subject_candidates = context.subject_analysis.get("subject_career_candidates", {})

    # Collect candidate careers from strong subjects, then from
    # demonstrated skills, de-duplicating while preserving order.
    candidate_titles: List[str] = []
    for careers in subject_candidates.values():
        candidate_titles.extend(careers)
    for skill in context.skill_analysis.get("demonstrated_skills", []):
        candidate_titles.extend(cm.get_careers_for_skill(skill))

    if not candidate_titles:
        candidate_titles = cm.DEFAULT_SUBJECT_CAREERS

    seen = set()
    recommendations: List[CareerRecommendation] = []
    for title in candidate_titles:
        if title in seen:
            continue
        seen.add(title)
        recommendations.append(
            CareerRecommendation(
                title=title,
                category=DEFAULT_CAREER_CATEGORY,
                match_score=60,  # neutral, non-AI-derived confidence score
                reason=(
                    f"Suggested based on {profile.name.split()[0] if profile.name else 'the student'}'s "
                    "current strong subjects and demonstrated skills."
                ),
                required_skills=[],
                roadmap=[],
            )
        )
        if len(recommendations) >= MAX_CAREER_RECOMMENDATIONS:
            break

    summary = (
        f"{profile.name} is currently performing at {profile.overall_score:.0f}% overall. "
        "The suggestions below are based directly on strong subjects and recorded "
        "achievements, and will improve once AI-powered guidance is available."
    )

    parent_guidance = [
        "Discuss the subjects your child enjoys most and why.",
        "Encourage exploring one new activity related to a strong subject this month.",
    ]
    if profile.attendance_percentage and profile.attendance_percentage < GOOD_ATTENDANCE_THRESHOLD:
        parent_guidance.append("Prioritise consistent attendance — it directly supports the scores above.")

    return AIResponse(
        success=True,
        source=SOURCE_FALLBACK,
        student_name=profile.name,
        summary=summary,
        career_recommendations=recommendations,
        parent_guidance=parent_guidance,
        future_skills=cm.FUTURE_SKILLS[:MAX_FUTURE_SKILLS],
        learning_roadmap=[
            "Identify one strong subject to explore beyond the classroom syllabus.",
            "Set a modest, specific goal for the current weakest subject.",
            "Revisit this roadmap next term as new academic data comes in.",
        ],
        error_message=reason or None,
    )


# =============================================================================
# SMALL, PRIVATE UTILITIES
# =============================================================================
def _safe_float(value: Any, default: float = 0.0) -> float:
    """Converts a value to float, tolerating None/blank/non-numeric input."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Converts a value to int, tolerating None/blank/non-numeric input."""
    if value is None or value == "":
        return default
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _derive_strengths(
    academic_summary: Optional[Dict[str, Any]],
    achievements: Optional[List[Dict[str, Any]]],
) -> List[str]:
    """
    Produces a short list of human-readable 'strengths' by combining
    the top academic subject with skills implied by achievements.
    Used only for StudentProfile.strengths — a lightweight signal,
    not a full analysis (that's build_skill_analysis's job).
    """
    strengths: List[str] = []
    top_subject = (academic_summary or {}).get("top_subject") or {}
    if top_subject.get("name"):
        strengths.append(top_subject["name"])

    for achievement in (achievements or [])[:3]:
        category = achievement.get("category", "")
        skills = cm.get_skills_for_achievement_category(category)
        strengths.extend(skills[:1])  # just the top skill per achievement, avoid noise

    # De-duplicate, preserve order
    seen = set()
    unique = []
    for s in strengths:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique