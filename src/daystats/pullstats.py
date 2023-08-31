from __future__ import annotations

import datetime
import dataclasses
import json
from typing import Any

import httpx

BASE_URL = "https://api.github.com/graphql"
TOKEN = ""
HEADERS = {"Authorization": f"bearer {TOKEN}"}
NOW_ISO8601 = datetime.datetime.now().strftime("%Y-%m-%d") + "T00:00:00.000Z"


def create_contrib_query(loginname: str, today: str) -> dict[str, Any]:
    """Return the query."""
    query = """
query($loginname: String!, $today:DateTime) {
    user(login:$loginname) {
        contributionsCollection(from:$today) {
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
        "today": today,
    }
    return {"query": query, "variables": variables}


def create_diff_query(
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


def fetch_contributions(loginname: str, today: str) -> Contributions:
    """Fetch contribution information from GitHub GraphQL API."""
    query = create_contrib_query(loginname, today)

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
    url: str


def fetch_pull_requests(
    author: str,
    repoowner: str,
    reponame: str,
    start: datetime.datetime,
    end: datetime.datetime,
) -> list[PullRequest]:
    """Fetch list of pull request details from GitHub GraphQL API."""
    cursor = None
    more = True
    prs = []

    while more:
        query = create_diff_query(repoowner, reponame, cursor)
        resp = httpx.post(BASE_URL, json=query, headers=HEADERS)
        if not resp.is_success or "data" not in resp.json():
            print(json.dumps(resp.json(), indent=4))
            raise ValueError("Unexpected response from API.")

        rjson = resp.json()["data"]["repository"]["pullRequests"]

        cursor = rjson["pageInfo"]["endCursor"]
        more = rjson["pageInfo"]["hasNextPage"]

        # print(json.dumps(resp.json(), indent=4))

        for node in rjson["nodes"]:
            updated = datetime.datetime.fromisoformat(node["updatedAt"].rstrip("Z"))

            if node["author"]["login"] != author:
                continue

            if updated.date() > end.date():
                continue

            if updated.date() < start.date():
                more = False
                break

            prs.append(
                PullRequest(
                    additions=node["additions"],
                    deletions=node["deletions"],
                    files=node["changedFiles"],
                    url=node["url"],
                )
            )

    return prs


def runner() -> int:
    """Run the program."""
    # TODO: These will need to be in the config
    timezone_offset = -5
    loginname = "Preocts"

    # TODO: GitHub operates in UTC so some timezone joy will be needed
    now = datetime.datetime.now()
    # REMOVE THIS
    now = now.replace(month=8, day=30)
    offset = datetime.timedelta(hours=timezone_offset)
    start_utc = now.replace(hour=0, minute=0, second=0, microsecond=0) + offset
    end_utc = now.replace(hour=23, minute=59, second=59, microsecond=0) + offset

    contribs = fetch_contributions(loginname, start_utc.isoformat() + "Z")
    print(contribs)

    for repo in contribs.pr_repos:
        pull_requests = fetch_pull_requests(
            author=loginname,
            repoowner=repo.owner,
            reponame=repo.name,
            start=start_utc,
            end=end_utc,
        )
        for pr in pull_requests:
            print(pr)

    return 0


if __name__ == "__main__":
    raise SystemExit(runner())
