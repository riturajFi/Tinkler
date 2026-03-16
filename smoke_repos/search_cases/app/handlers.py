def build_index() -> dict[str, int]:
    return {"docs": 3, "notes": 7}


def resolve_issue(issue_id: str) -> str:
    return f"resolved:{issue_id}"
