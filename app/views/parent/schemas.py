"""
schemas.py
=====================================================================
Typed data structures shared across the career guidance module.

Using plain `dataclasses` (rather than requiring Pydantic as a hard
dependency) keeps this module lightweight and easy to drop into any
Django project. Each dataclass exposes `.to_dict()` so instances can
be serialized straight into a template context or a JSON API response.

If your project already depends on Pydantic and you'd prefer stricter
runtime validation, these classes translate 1:1 into BaseModel
subclasses — the field shapes would not need to change.
=====================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Student Profile
# ---------------------------------------------------------------------------
@dataclass
class StudentProfile:
    """A flattened, AI-friendly summary of who the student is."""

    name: str
    std: str
    division: str
    overall_score: float
    attendance_percentage: float
    top_subjects: List[str] = field(default_factory=list)
    weak_subjects: List[str] = field(default_factory=list)
    learning_style: str = "Balanced"
    interests: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    has_remedial_support: bool = False
    achievement_count: int = 0
    project_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Career Context — the single object passed into the AI
# ---------------------------------------------------------------------------
@dataclass
class CareerContext:
    """
    Everything the AI needs to generate career guidance, pre-computed
    and flattened. This is the boundary object between dashboard.py
    (which knows about the database) and ai.py (which does not).
    """

    student_profile: StudentProfile
    learning_profile: Dict[str, Any] = field(default_factory=dict)
    strength_analysis: Dict[str, Any] = field(default_factory=dict)
    skill_analysis: Dict[str, Any] = field(default_factory=dict)
    subject_analysis: Dict[str, Any] = field(default_factory=dict)

    # Kept for prompts that want richer, less-processed context
    # (e.g. exact achievement titles rather than derived skill tags).
    raw_achievements: List[Dict[str, Any]] = field(default_factory=list)
    raw_projects: List[Dict[str, Any]] = field(default_factory=list)
    behaviour_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_profile": self.student_profile.to_dict(),
            "learning_profile": self.learning_profile,
            "strength_analysis": self.strength_analysis,
            "skill_analysis": self.skill_analysis,
            "subject_analysis": self.subject_analysis,
            "raw_achievements": self.raw_achievements,
            "raw_projects": self.raw_projects,
            "behaviour_notes": self.behaviour_notes,
        }


# ---------------------------------------------------------------------------
# A single recommended career
# ---------------------------------------------------------------------------
@dataclass
class CareerRecommendation:
    title: str
    category: str
    match_score: int  # 0-100, how strongly this fits the student
    reason: str
    required_skills: List[str] = field(default_factory=list)
    roadmap: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# The final response shape returned to dashboard.py / the view
# ---------------------------------------------------------------------------
@dataclass
class AIResponse:
    """
    Consistent response envelope regardless of whether the content
    came from Gemini or the rule-based fallback. Callers (views,
    templates) should never need to branch on `source` to know which
    fields exist — the shape is always the same.
    """

    success: bool
    source: str  # "gemini" | "fallback" | "cache"
    student_name: str
    summary: str
    career_recommendations: List[CareerRecommendation] = field(default_factory=list)
    parent_guidance: List[str] = field(default_factory=list)
    future_skills: List[Dict[str, str]] = field(default_factory=list)
    learning_roadmap: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "source": self.source,
            "student_name": self.student_name,
            "summary": self.summary,
            "career_recommendations": [c.to_dict() for c in self.career_recommendations],
            "parent_guidance": self.parent_guidance,
            "future_skills": self.future_skills,
            "learning_roadmap": self.learning_roadmap,
            "generated_at": self.generated_at,
            "error_message": self.error_message,
        }