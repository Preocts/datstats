from __future__ import annotations

import datetime
import json
import os
import pathlib
from unittest.mock import MagicMock
from unittest.mock import patch

from daystats import daystats
from daystats.daystats import BASE_URL
from daystats.daystats import TOKEN_KEY

CONTRIBUTION_FIXTURE = pathlib.Path("tests/fixture_contribution.json").read_text()


def test_HTTPClient_headers() -> None:
    """Sanity check that User-Agent exists and token is used."""
    client = daystats.HTTPClient("mock_token")

    assert client._headers["Authorization"] == "bearer mock_token"
    assert "User-Agent" in client._headers


def test_HTTPClient_cleans_url_and_splits_on_init() -> None:
    """Using http.client means no https://"""
    client = daystats.HTTPClient("mock", "https://example.com/foobar/baz")

    assert client._host == "example.com"
    assert client._path == "foobar/baz"


def test_HTTPClient_cleans_url_and_handles_no_path() -> None:
    """Custom host or proxy edge-case"""
    client = daystats.HTTPClient("mock", "https://example.com")

    assert client._host == "example.com"
    assert client._path == ""


def test_HTTPClient_post_returns_expected_mock_response() -> None:
    """Do not test the call, only the handling of a valid JSON response."""
    # One day I'll give up using http.client. Not today though.
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value.read.return_value = b'{"foobar": "baz"}'
    client = daystats.HTTPClient("mock", "https://mock.com/path")

    with patch("http.client") as mock_httpclient:
        mock_httpclient.HTTPSConnection.return_value = mock_conn
        resp = client.post({})

    assert resp == {"foobar": "baz"}
    mock_httpclient.HTTPSConnection.assert_called_with(
        "mock.com",
        timeout=daystats.HTTPS_TIMEOUT,
    )
    mock_conn.request.assert_called_with("POST", "/path", "{}", client._headers)


def test_HTTPClient_post_returns_error_on_issue() -> None:
    mock_conn = MagicMock()
    mock_conn.getresponse.return_value.read.return_value = b"foobar"
    client = daystats.HTTPClient("mock", "https://mock.com/path")

    with patch("http.client") as mock_httpclient:
        mock_httpclient.HTTPSConnection.return_value = mock_conn
        resp = client.post({})

    assert "error" in resp


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

    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = mock_now

        start, end = daystats._build_bookend_times()

    assert start.isoformat() == "1998-12-31T00:00:00"
    assert end.isoformat() == "1998-12-31T23:59:59"


def test_build_bookend_from_cli_time() -> None:
    """Controll datetime.datetime.now and build bookends."""
    mock_now = datetime.datetime(year=1998, month=12, day=31, hour=12, minute=23)

    with patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = mock_now

        start, end = daystats._build_bookend_times(1999, 12, 31)

    assert start.isoformat() == "1999-12-31T00:00:00"
    assert end.isoformat() == "1999-12-31T23:59:59"


def test_fetch_contributions_successful_parsing() -> None:
    """Do not test the call, only parsing logic of expected results"""
    client = daystats.HTTPClient("mock", "example.com")
    mock_resp = json.loads(CONTRIBUTION_FIXTURE)
    start = datetime.datetime(year=1998, month=12, day=31, hour=0, minute=0, second=0)
    end = datetime.datetime(year=1998, month=12, day=31, hour=23, minute=59, second=59)

    with patch.object(client, "post", return_value=mock_resp):
        result = daystats.fetch_contributions(client, "mockname", start, end)

    assert result
    assert result.commits == 5
    assert result.issues == 1
    assert result.reviews == 0
    assert result.pullrequests == 2
    assert len(result.pr_repos) == 1
    assert list(result.pr_repos)[0].name == "daystats"
    assert list(result.pr_repos)[0].owner == "Preocts"


def test_fetch_contributions_error_handled() -> None:
    client = daystats.HTTPClient("mock", "example.com")
    mock_resp = {"error": "json machine broken"}
    start = datetime.datetime(year=1998, month=12, day=31, hour=0, minute=0, second=0)
    end = datetime.datetime(year=1998, month=12, day=31, hour=23, minute=59, second=59)

    with patch.object(client, "post", return_value=mock_resp):
        result = daystats.fetch_contributions(client, "mockname", start, end)

    assert result is None


# times for repository tests
# 2023-08-31 19:00:00 2023-09-01 18:59:59
