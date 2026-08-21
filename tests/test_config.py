from datetime import date

from vantage.config import Settings


def test_default_scope_is_asi_corridor():
    settings = Settings()
    settings.validate()
    assert settings.airports == ("ORD", "JFK", "ATL")
    assert settings.start_date == date(2024, 6, 1)


def test_invalid_date_window_is_rejected():
    settings = Settings(start_date=date(2024, 9, 1), end_date=date(2024, 8, 1))
    try:
        settings.validate()
    except ValueError as error:
        assert "on or before" in str(error)
    else:
        raise AssertionError("expected invalid date window to fail")

