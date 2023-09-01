from __future__ import annotations

import os
from unittest.mock import patch

from daystats import daystats
from daystats.daystats import BASE_URL
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
