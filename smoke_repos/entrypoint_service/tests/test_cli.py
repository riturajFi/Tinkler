from src.cli import main


def test_main_exists() -> None:
    assert callable(main)
