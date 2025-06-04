CALENDAR_ALIAS_MAP = {
    "my calendar": "primary", # Google's default calendar
    "work calendar": "oguguofrank246@gmail.com",
    "personal calendar": "nnatuanyafrank@gmail.com",
    "team calendar": "project-team@example.com",
}

def resolve_calendar_id(alias: str) -> str:
    """
    Resolve a calendar alias to its corresponding calendar ID.
    """
    alias_lower = (alias or "").strip().lower()   # Normalize alias to lowercase and strip whitespace
    return CALENDAR_ALIAS_MAP.get(alias_lower, "primary") #fallback to 'primary'


