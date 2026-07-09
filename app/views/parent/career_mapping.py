"""
career_mapping.py
=====================================================================
Maintainable, data-only mappings used in two places:

1. By ai.py's builder functions (build_skill_analysis, etc.) to turn
   raw academic/achievement data into structured "skill tags" before
   they're sent to Gemini — this gives the AI cleaner signal instead
   of raw subject names.

2. By ai.py's fallback_response() as a rule-based substitute when
   Gemini is unavailable, so the module still returns *something*
   useful without ever calling the AI.

Everything here is plain data (dicts/lists) on purpose — no logic.
Extending career coverage should never require touching ai.py.
=====================================================================
"""

from typing import Dict, List


# ---------------------------------------------------------------------------
# Subject -> Careers
# ---------------------------------------------------------------------------
SUBJECT_CAREER_MAP: Dict[str, List[str]] = {
    "Mathematics": ["Data Scientist", "Actuary", "Software Engineer", "Financial Analyst", "Architect"],
    "Science": ["Doctor", "Research Scientist", "Biotechnologist", "Pharmacist", "Environmental Scientist"],
    "Physics": ["Aerospace Engineer", "Mechanical Engineer", "Robotics Engineer", "Astrophysicist"],
    "Chemistry": ["Chemical Engineer", "Pharmacist", "Forensic Scientist", "Materials Scientist"],
    "Biology": ["Doctor", "Geneticist", "Biotechnologist", "Veterinarian", "Microbiologist"],
    "Computer Science": ["Software Engineer", "AI/ML Engineer", "Cybersecurity Analyst", "Game Developer"],
    "English": ["Journalist", "Content Writer", "Lawyer", "Editor", "Public Relations Specialist"],
    "Social Science": ["Civil Servant", "Lawyer", "Historian", "Policy Analyst", "Sociologist"],
    "Geography": ["Urban Planner", "Environmental Scientist", "Cartographer", "Geologist"],
    "History": ["Historian", "Archaeologist", "Museum Curator", "Civil Servant"],
    "Economics": ["Economist", "Financial Analyst", "Investment Banker", "Policy Advisor"],
    "Art": ["Graphic Designer", "Animator", "UI/UX Designer", "Illustrator", "Architect"],
    "Physical Education": ["Sports Scientist", "Physiotherapist", "Athletic Coach", "Sports Management"],
    "Computer Applications": ["Software Engineer", "Data Analyst", "IT Consultant", "Web Developer"],
}

DEFAULT_SUBJECT_CAREERS: List[str] = ["Research Analyst", "Consultant", "Entrepreneur"]


# ---------------------------------------------------------------------------
# Achievement category -> Skills demonstrated
# ---------------------------------------------------------------------------
ACHIEVEMENT_SKILL_MAP: Dict[str, List[str]] = {
    "academic": ["Analytical Thinking", "Discipline", "Subject Mastery"],
    "sports": ["Teamwork", "Discipline", "Resilience", "Leadership", "Time Management"],
    "arts": ["Creativity", "Attention to Detail", "Self-Expression", "Originality"],
    "leadership": ["Leadership", "Communication", "Decision Making", "Public Speaking"],
    "technology": ["Problem Solving", "Logical Reasoning", "Technical Aptitude"],
    "community_service": ["Empathy", "Social Responsibility", "Collaboration"],
    "debate": ["Public Speaking", "Critical Thinking", "Persuasion", "Research"],
    "music": ["Discipline", "Creativity", "Focus", "Pattern Recognition"],
}

DEFAULT_ACHIEVEMENT_SKILLS: List[str] = ["Initiative", "Commitment"]

SKILL_CAREER_MAP: Dict[str, List[str]] = {
    "Analytical Thinking": ["Data Scientist", "Actuary", "Research Analyst"],
    "Creativity": ["Graphic Designer", "Animator", "Content Creator", "Architect"],
    "Leadership": ["Entrepreneur", "Project Manager", "Civil Servant"],
    "Communication": ["Journalist", "Lawyer", "Public Relations Specialist", "Teacher"],
    "Problem Solving": ["Software Engineer", "Engineer", "Consultant"],
    "Empathy": ["Doctor", "Psychologist", "Social Worker", "Counsellor"],
    "Public Speaking": ["Lawyer", "Politician", "Teacher", "News Anchor"],
    "Technical Aptitude": ["Software Engineer", "Robotics Engineer", "IT Consultant"],
    "Discipline": ["Armed Forces Officer", "Athlete", "Pilot"],
    "Attention to Detail": ["Editor", "Auditor", "Quality Analyst", "Surgeon"],
}


# ---------------------------------------------------------------------------
# Interest keyword -> Careers
# (Matched loosely against free-text interests if the frontend collects them)
# ---------------------------------------------------------------------------
INTEREST_CAREER_MAP: Dict[str, List[str]] = {
    "space": ["Aerospace Engineer", "Astrophysicist", "Astronomer"],
    "animals": ["Veterinarian", "Zoologist", "Wildlife Biologist"],
    "coding": ["Software Engineer", "Game Developer", "AI/ML Engineer"],
    "drawing": ["Graphic Designer", "Animator", "Illustrator"],
    "helping people": ["Doctor", "Social Worker", "Psychologist", "Teacher"],
    "business": ["Entrepreneur", "Investment Banker", "Marketing Manager"],
    "sports": ["Athlete", "Sports Scientist", "Coach", "Sports Journalist"],
    "environment": ["Environmental Scientist", "Conservationist", "Urban Planner"],
    "writing": ["Journalist", "Author", "Content Writer", "Screenwriter"],
    "gaming": ["Game Developer", "Game Designer", "Esports Analyst"],
}


# ---------------------------------------------------------------------------
# Personality trait -> Careers
# (Useful if learning_rhythm / behaviour_data exposes trait-like signals)
# ---------------------------------------------------------------------------
PERSONALITY_CAREER_MAP: Dict[str, List[str]] = {
    "introvert_analytical": ["Data Scientist", "Researcher", "Software Engineer", "Accountant"],
    "extrovert_expressive": ["Lawyer", "Journalist", "Politician", "Sales Manager"],
    "hands_on_practical": ["Engineer", "Surgeon", "Chef", "Pilot"],
    "creative_independent": ["Designer", "Artist", "Entrepreneur", "Writer"],
    "structured_methodical": ["Actuary", "Auditor", "Civil Servant", "Project Manager"],
}


# ---------------------------------------------------------------------------
# Future / emerging skills — used for the "Future Skills" section
# ---------------------------------------------------------------------------
FUTURE_SKILLS: List[Dict[str, str]] = [
    {
        "name": "AI & Machine Learning Literacy",
        "description": "Understanding how AI systems work and how to use them effectively.",
        "why_it_matters": "Nearly every future career will involve working alongside AI tools.",
    },
    {
        "name": "Data Literacy",
        "description": "Reading, interpreting, and drawing conclusions from data and charts.",
        "why_it_matters": "Decision-making across all fields is increasingly data-driven.",
    },
    {
        "name": "Critical Thinking",
        "description": "Evaluating information and arguments rather than accepting them at face value.",
        "why_it_matters": "Essential for navigating a world with abundant, often conflicting, information.",
    },
    {
        "name": "Communication & Storytelling",
        "description": "Explaining ideas clearly to different audiences, in writing and speech.",
        "why_it_matters": "Technical skill alone rarely gets ideas adopted — clear communication does.",
    },
    {
        "name": "Adaptability",
        "description": "Comfort with learning new tools and shifting approaches as fields evolve.",
        "why_it_matters": "Most students will work in roles that don't exist yet.",
    },
    {
        "name": "Collaboration",
        "description": "Working effectively in teams, including with people from different backgrounds.",
        "why_it_matters": "Most meaningful work today is cross-disciplinary and team-based.",
    },
]


# ---------------------------------------------------------------------------
# Helper accessors
# ---------------------------------------------------------------------------
def get_careers_for_subject(subject_name: str) -> List[str]:
    """Case-insensitive lookup with a sensible default."""
    for key, careers in SUBJECT_CAREER_MAP.items():
        if key.lower() == (subject_name or "").strip().lower():
            return careers
    return DEFAULT_SUBJECT_CAREERS


def get_skills_for_achievement_category(category: str) -> List[str]:
    return ACHIEVEMENT_SKILL_MAP.get((category or "").strip().lower(), DEFAULT_ACHIEVEMENT_SKILLS)


def get_careers_for_skill(skill: str) -> List[str]:
    return SKILL_CAREER_MAP.get(skill, [])


def get_careers_for_interest(interest_text: str) -> List[str]:
    """Loose substring match against known interest keywords."""
    text = (interest_text or "").lower()
    matches: List[str] = []
    for keyword, careers in INTEREST_CAREER_MAP.items():
        if keyword in text:
            matches.extend(careers)
    return matches
    