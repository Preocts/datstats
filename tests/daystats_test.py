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
REPOSITORY_FIXTURE = pathlib.Path("tests/fixture_repository_paged.json").read_text()


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
        "--debug",
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

    assert result.commits == 0
    assert result.issues == 0
    assert result.reviews == 0
    assert result.pullrequests == 0
    assert result.pr_repos == set()


def test_fetch_pull_requets_successful_parsing() -> None:
    """Do not test the call, only parsing logic of expected results"""
    client = daystats.HTTPClient("mock", "example.com")
    mock_resp = json.loads(REPOSITORY_FIXTURE)
    # times for repository fixture
    # 2023-08-31 19:00:00 2023-09-01 18:59:59
    start = datetime.datetime(year=2023, month=8, day=31, hour=19, minute=0, second=0)
    end = datetime.datetime(year=2023, month=9, day=1, hour=18, minute=59, second=59)

    with patch.object(client, "post", side_effect=mock_resp):
        result = daystats.fetch_pull_requests(
            client=client,
            author="preocts",
            repoowner="preocts",
            reponame="daystats",
            start_dt=start,
            end_dt=end,
        )

    assert len(result) == 3
    assert result[0].additions == 47
    assert result[0].deletions == 286
    assert result[0].files == 10
    assert result[0].created_at == "2023-09-01T04:51:04Z"
    assert result[0].url == "https://github.com/Preocts/daystats/pull/5"
    assert result[0].number == 5
    assert result[0].reponame == "daystats"


def test_fetch_pull_requets_error_handle() -> None:
    """Do not test the call, only parsing logic of expected results"""
    client = daystats.HTTPClient("mock", "example.com")
    mock_resp = {"error": "json machine broken"}
    start = datetime.datetime(year=2023, month=8, day=31, hour=19, minute=0, second=0)
    end = datetime.datetime(year=2023, month=9, day=1, hour=18, minute=59, second=59)

    with patch.object(client, "post", return_value=mock_resp):
        result = daystats.fetch_pull_requests(
            client=client,
            author="preocts",
            repoowner="preocts",
            reponame="daystats",
            start_dt=start,
            end_dt=end,
        )

    assert result == []


def test_get_stats() -> None:
    """Assert our "do it all" function calls as expected"""

    class MockRepo:
        owner = "mock"
        name = "mock"

    class MockContrib:
        pr_repos = [MockRepo(), MockRepo()]

    client = daystats.HTTPClient("mock", "example.com")
    mock_contrib = MockContrib()

    with patch.object(daystats, "fetch_contributions") as mock_fetch_contrib:
        with patch.object(daystats, "fetch_pull_requests") as mock_fetch_pr:
            mock_fetch_contrib.return_value = mock_contrib
            contribs, prs = daystats.get_stats(client, "preocts")

    assert mock_fetch_contrib.call_count == 1
    assert mock_fetch_pr.call_count == 2

    assert contribs is mock_contrib
    assert prs == []


def test_runner() -> None:
    """Assert our cli entry point calls as expected"""
    args = [
        "mock",
        *("--day", "12"),
        *("--month", "31"),
        *("--year", "1998"),
        *("--url", "https://github.com/broken"),
        *("--token", "mock_token"),
    ]
    with patch.object(daystats, "get_stats") as mock_get_stats:
        mock_get_stats.return_value = ("Hello", ["Hello", "World"])

        result = daystats.runner(args)

    call_kwargs = mock_get_stats.call_args[1]
    assert call_kwargs["client"]._token == "mock_token"
    assert call_kwargs["client"]._host == "github.com"
    assert call_kwargs["loginname"] == "mock"
    assert call_kwargs["day"] == 12
    assert call_kwargs["month"] == 31
    assert call_kwargs["year"] == 1998
    assert result == 0


def test_stats_to_markdown_expected_output() -> None:
    """Assert our output doesn't change without awareness."""
    expected = """\

**Daily GitHub Summary**:

| Contribution | Count | Metric | Total |
| -- | -- | -- | -- |
| Reviews | 1 | Files Changed | 12 |
| Issues | 1 | Additions | 12 |
| Commits | 1 | Deletions | 12 |
| Pull Requests | 1 | | |

**Pull Request Breakdown**:

| Repo | Addition | Deletion | Files | Number |
| -- | -- | -- | -- | -- |
| mock | 12 | 12 | 12 | [see: #1](https://mock) |"""
    contrib = daystats.Contributions(1, 1, 1, 1, pr_repos=set())
    pulls = [daystats.PullRequest("mock", 12, 12, 12, "sometime", 1, "https://mock")]

    result = daystats.stats_to_markdown(contrib, pulls)

    assert result == expected


def test_stats_to_text_expected_output() -> None:
    """Assert our output doesn't change without awareness."""
    expected = """\

Daily GitHub Summary:
|    Contribution    | Count |    Metric     | Total |
------------------------------------------------------
| Reviews            |   1   | Files Changed |  12   |
| Issue              |   1   | Additions     |  12   |
| Commits            |   1   | Deletions     |  12   |
| Pull Requests      |   1   |               |       |

Pull Request Breakdown:

| Addition | Deletion | Files | Number | Url
----------------------------------------
|    12    |    12    |  12   |   1    | https://mock"""
    contrib = daystats.Contributions(1, 1, 1, 1, pr_repos=set())
    pulls = [daystats.PullRequest("mock", 12, 12, 12, "sometime", 1, "https://mock")]

    result = daystats.stats_to_text(contrib, pulls)

    assert result == expected
