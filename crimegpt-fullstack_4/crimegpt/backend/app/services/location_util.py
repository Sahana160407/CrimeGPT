def is_location_restricted(current_user: dict) -> bool:
    """True for any non-Admin user with a real (non-'All') office location."""
    loc = current_user.get("officeLocation")
    return current_user.get("role") != "Admin" and bool(loc) and loc != "All"


def user_location(current_user: dict) -> str | None:
    return current_user.get("officeLocation")
