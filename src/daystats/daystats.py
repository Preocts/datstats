from __future__ import annotations

import argparse
import dataclasses
import datetime
import http.client
import json
import os
import time
from typing import Any

import httpx
import secretbox

# This couldn't possibily be a bad way to get the UTC offset :3c
TIMEZONE_OFFSET = datetime.timedelta(hours=time.timezone // 60 // 60)

BASE_URL = "https://api.github.com/graphql"
TOKEN_KEY = "DAILYSTATS_PAT"
HTTPS_TIMEOUT = 10  # seconds

TOKEN = secretbox.SecretBox(auto_load=True).get(TOKEN_KEY)
HEADERS = {"Authorization": f"bearer {TOKEN}"}
NOW_ISO8601 = datetime.datetime.now().strftime("%Y-%m-%d") + "T00:00:00.000Z"


class HTTPClient:
    def __init__(self, token: str | None, url: str = BASE_URL) -> None:
        """Define an HTTPClient with token and target GitHub GraphQL API url."""
        self._token = token or ""
        url = url.lower().replace("https://", "").replace("http://", "")
        url_split = url.split("/", 1)
        self._host = url_split[0]
        self._path = url_split[1] if len(url_split) > 1 else ""

    @property
    def _headers(self) -> dict[str, str]:
        return {"User-Agent": "egg-daystats", "Authorization": f"bearer {self._token}"}

    def post(self, data: dict[str, Any]) -> dict[str, Any]:
        """Post JSON serializable data to GitHub GraphQL API, return reponse."""
        connection = http.client.HTTPSConnection(self._host, timeout=HTTPS_TIMEOUT)
        connection.request("POST", f"/{self._path}", json.dumps(data), self._headers)
        resp = connection.getresponse()

        try:
            resp_json = json.loads(resp.read().decode())
        except json.JSONDecodeError as err:
            return {"error": str(err)}

        return resp_json


def _create_contrib_query(loginname: str, from_: str, to_: str) -> dict[str, Any]:
    """Return the query."""
    query = """
query($loginname: String!, $from_time:DateTime, $to_time:DateTime) {
    user(login:$loginname) {
        contributionsCollection(from:$from_time, to:$to_time) {
            totalCommitContributions
            totalIssueContributions
            totalPullRequestContributions
            totalPullRequestReviewContributions
            pullRequestContributionsByRepository {
                repository {
                    owner {
                        login
                    }
                    name
                }
            }
        }
    }
}"""
    variables = {
        "loginname": loginname,
        "from_time": from_,
        "to_time": to_,
    }
    return {"query": query, "variables": variables}


def _create_diff_query(
    repoowner: str,
    reponame: str,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Return the query."""
    query = """
query($repoowner: String!, $reponame: String!, $cursor: String) {
    repository(name:$reponame, owner:$repoowner) {
        pullRequests(orderBy: {field:CREATED_AT, direction:DESC}, first:25, after:$cursor) {
            totalCount
            pageInfo {
                endCursor
                hasNextPage
                hasPreviousPage
                startCursor
            }
            nodes {
                author {
                    login
                }
                createdAt
                updatedAt
                additions
                deletions
                changedFiles
                url
            }
        }
    }
}"""
    variables = {
        "cursor": cursor,
        "repoowner": repoowner,
        "reponame": reponame,
    }
    return {"query": query, "variables": variables}


@dataclasses.dataclass(frozen=True)
class Repo:
    owner: str
    name: str


@dataclasses.dataclass(frozen=True)
class Contributions:
    commits: int
    issues: int
    pullrequests: int
    reviews: int
    pr_repos: set[Repo]


def fetch_contributions(
    loginname: str,
    start_dt: datetime.datetime,
    end_dt: datetime.datetime,
) -> Contributions:
    """
    Fetch contribution information from GitHub GraphQL API.

    start_dt and end_dt are the local time `.now()` without a UTC offset
    """
    # Odd that we are giving GitHub our local time but labeling it as zulu
    # yet GitHub will return the correct contribution activity with the
    # incorrectly set timezone.
    from_ = start_dt.isoformat() + "Z"
    to_ = end_dt.isoformat() + "Z"
    query = _create_contrib_query(loginname, from_, to_)

    resp = httpx.post(BASE_URL, json=query, headers=HEADERS)
    if not resp.is_success or "data" not in resp.json():
        print(json.dumps(resp.json(), indent=4))
        raise ValueError("Unexpected response from API.")

    pr_repos = set()
    rjson = resp.json()
    contribs = rjson["data"]["user"]["contributionsCollection"]

    for pr in contribs["pullRequestContributionsByRepository"]:
        repo = Repo(
            owner=pr["repository"]["owner"]["login"],
            name=pr["repository"]["name"],
        )
        pr_repos.add(repo)

    # print(json.dumps(resp.json(), indent=4))
    return Contributions(
        commits=contribs["totalCommitContributions"],
        issues=contribs["totalIssueContributions"],
        pullrequests=contribs["totalPullRequestContributions"],
        reviews=contribs["totalPullRequestReviewContributions"],
        pr_repos=pr_repos,
    )


@dataclasses.dataclass(frozen=True)
class PullRequest:
    additions: int
    deletions: int
    files: int
    created_at: str
    url: str


def fetch_pull_requests(
    author: str,
    repoowner: str,
    reponame: str,
    start_dt: datetime.datetime,
    end_dt: datetime.datetime,
) -> list[PullRequest]:
    """
    Fetch list of pull request details from GitHub GraphQL API.

    Unlike fetch contributions, the start_dt and end_dt must be offset to UTC
    in order to correctly filter the activity.

    Args:
        author: Results filtered to only include Author of pull request
        repoowner: Owner of repo (or org)
        reponame: Name of repo
        start_dt: Earliest created at time for pull request
        end_dt: Latest created at time for pull request
    """
    cursor = None
    more = True
    prs = []

    while more:
        query = _create_diff_query(repoowner, reponame, cursor)
        resp = httpx.post(BASE_URL, json=query, headers=HEADERS)
        if not resp.is_success or "data" not in resp.json():
            print(json.dumps(resp.json(), indent=4))
            raise ValueError("Unexpected response from API.")

        rjson = resp.json()["data"]["repository"]["pullRequests"]

        cursor = rjson["pageInfo"]["endCursor"]
        more = rjson["pageInfo"]["hasNextPage"]

        # print(json.dumps(resp.json(), indent=4))

        for node in rjson["nodes"]:
            created_at = datetime.datetime.fromisoformat(node["createdAt"].rstrip("Z"))

            if node["author"]["login"] != author:
                continue

            if created_at > end_dt:
                continue

            if created_at < start_dt:
                more = False
                break

            prs.append(
                PullRequest(
                    additions=node["additions"],
                    deletions=node["deletions"],
                    files=node["changedFiles"],
                    created_at=node["createdAt"],
                    url=node["url"],
                )
            )

    return prs


@dataclasses.dataclass(frozen=True)
class CLIArgs:
    loginname: str
    year: int | None = None
    month: int | None = None
    day: int | None = None
    url: str = BASE_URL
    token: str | None = None


def parse_args(cli_args: list[str] | None = None) -> CLIArgs:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="daystats",
        description="Pull daily stats from GitHub.",
    )
    parser.add_argument(
        "loginname",
        type=str,
        help="Login name to GitHub (author name).",
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Year to query. (default: today)",
    )
    parser.add_argument(
        "--month",
        type=int,
        help="Month of the year to query. (default: today)",
    )
    parser.add_argument(
        "--day",
        type=int,
        help="Day of the month to query. (default: today)",
    )
    parser.add_argument(
        "--url",
        type=str,
        help=f"Override default GitHub GraphQL API url. (default: {BASE_URL})",
        default=BASE_URL,
    )
    parser.add_argument(
        "--token",
        type=str,
        help=f"GitHub Personal Access Token with read-only access for publis repos. Defaults to ${TOKEN_KEY} environ variable.",
        default=os.getenv(TOKEN_KEY),
    )

    args = parser.parse_args(cli_args)
    return CLIArgs(
        loginname=args.loginname,
        year=args.year,
        month=args.month,
        day=args.day,
        url=args.url,
        token=args.token,
    )


def _build_bookend_times(args: CLIArgs) -> tuple[datetime.datetime, datetime.datetime]:
    """Build start/end datetime ranges from 00:00 to 23:59."""
    now = datetime.datetime.now()

    if args.day:
        now = now.replace(day=args.day)

    if args.month:
        now = now.replace(month=args.month)

    if args.year:
        now = now.replace(year=args.year)

    start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = now.replace(hour=23, minute=59, second=59, microsecond=0)

    return start_dt, end_dt


def runner() -> int:
    """Run the program."""
    # args = parse_args()
    # client = HTTPClient(args.token, args.url)

    # contribs = fetch_contributions(loginname, start_dt, end_dt)
    # print(contribs)

    # for repo in contribs.pr_repos:
    #     pull_requests = fetch_pull_requests(
    #         author=loginname,
    #         repoowner=repo.owner,
    #         reponame=repo.name,
    #         start_dt=start_dt + offset,
    #         end_dt=end_dt + offset,
    #     )
    #     for pr in pull_requests:
    #         print(pr)

    return 0


if __name__ == "__main__":
    raise SystemExit(runner())
