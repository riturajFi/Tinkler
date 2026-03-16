from app.worker import run_worker


def test_worker_symbol_is_present() -> None:
    assert callable(run_worker)
