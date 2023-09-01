from __future__ import annotations

import datetime
import os
from unittest.mock import patch

from daystats import daystats
from daystats.daystats import BASE_URL
from daystats.daystats import CLIArgs
from daystats.daystats import TOKEN_KEY


def test_parse_args_defaults() -> None:
    """Assert parsing returns expected defaults."""
    args = ["mock"]
    env = {TOKEN_KEY: "mock_token"}

    with patch.dict(os.environ, env):
        result = daystats.parse_args(args)

    assert result.loginname == "mock"
    assert result.day is None
    assert result.month is None
    assert result.year is None
    assert result.url == BASE_URL
    assert result.token == "mock_token"


def test_parse_args_flags() -> None:
    """Assert flags override all."""
    env = {TOKEN_KEY: "mock_token"}
    args = [
        "mock",
        *("--day", "12"),
        *("--month", "31"),
        *("--year", "1998"),
        *("--url", "https://github.com/broken"),
        *("--token", "mockier_token"),
    ]

    with patch.dict(os.environ, env):
        result = daystats.parse_args(args)

    assert result.loginname == "mock"
    assert result.day == 12
    assert result.month == 31
    assert result.year == 1998
    assert result.url == "https://github.com/broken"
    assert result.token == "mockier_token"


def test_build_bookend_from_now() -> None:
    """Controll datetime.datetime.now and build bookends."""
    mock_now = datetime.datetime(year=1998, month=12, day=31, hour=12, minute=23)
    args = CLIArgs("fluffy")

    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = mock_now

        start, end = daystats._build_bookend_times(args)

    assert start.isoformat() == "1998-12-31T00:00:00"
    assert end.isoformat() == "1998-12-31T23:59:59"


def test_build_bookend_from_cli_time() -> None:
    """Controll datetime.datetime.now and build bookends."""
    mock_now = datetime.datetime(year=1998, month=12, day=31, hour=12, minute=23)
    args = CLIArgs("fluffy", year=1998, month=12, day=31)

    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = mock_now

        start, end = daystats._build_bookend_times(args)

    assert start.isoformat() == "1998-12-31T00:00:00"
    assert end.isoformat() == "1998-12-31T23:59:59"
