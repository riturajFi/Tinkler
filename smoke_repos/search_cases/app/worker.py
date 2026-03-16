from app.handlers import resolve_issue


def run_worker() -> None:
    result = resolve_issue("ISSUE-42")
    print(result)
