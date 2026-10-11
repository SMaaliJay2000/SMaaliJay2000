"""Fetch GitHub profile stats via the GraphQL API and write stats.json.

Env: GH_TOKEN (a PAT with `read:user` + `repo` also counts private repos;
the default Actions GITHUB_TOKEN counts public data only).
If anything fails, the previous stats.json is left untouched.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())
LOGIN = CONFIG["login"]
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def gql(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def main():
    if not TOKEN:
        sys.exit("No GH_TOKEN set; keeping existing stats.json")

    # profile basics
    q = """
    query($login:String!){
      user(login:$login){
        id createdAt
        followers{totalCount}
        repositoriesContributedTo(first:1, includeUserRepositories:false,
          contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){totalCount}
        repositories(ownerAffiliations:OWNER, isFork:false, first:100){
          totalCount
          nodes{ nameWithOwner stargazerCount }
          pageInfo{hasNextPage endCursor}
        }
      }
    }"""
    u = gql(q, {"login": LOGIN})["user"]
    uid = u["id"]
    repos = list(u["repositories"]["nodes"])
    page = u["repositories"]["pageInfo"]
    while page["hasNextPage"]:
        more = gql(
            """query($login:String!,$after:String){user(login:$login){
              repositories(ownerAffiliations:OWNER,isFork:false,first:100,after:$after){
                nodes{nameWithOwner stargazerCount} pageInfo{hasNextPage endCursor}}}}""",
            {"login": LOGIN, "after": page["endCursor"]},
        )["user"]["repositories"]
        repos += more["nodes"]
        page = more["pageInfo"]

    stars = sum(r["stargazerCount"] for r in repos)

    # commits: one request per calendar year since account creation
    created = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    commits = 0
    for year in range(created.year, now.year + 1):
        start = max(created, datetime(year, 1, 1, tzinfo=timezone.utc))
        end = min(now, datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
        c = gql(
            """query($login:String!,$from:DateTime!,$to:DateTime!){
              user(login:$login){contributionsCollection(from:$from,to:$to){
                totalCommitContributions restrictedContributionsCount}}}""",
            {"login": LOGIN, "from": start.isoformat(), "to": end.isoformat()},
        )["user"]["contributionsCollection"]
        commits += c["totalCommitContributions"] + c["restrictedContributionsCount"]

    # lines of code: additions/deletions of my commits in each owned repo
    added = deleted = 0
    for repo in repos:
        owner, name = repo["nameWithOwner"].split("/")
        after = None
        while True:
            r = gql(
                """query($o:String!,$n:String!,$uid:ID!,$after:String){
                  repository(owner:$o,name:$n){defaultBranchRef{target{... on Commit{
                    history(first:100,after:$after,author:{id:$uid}){
                      nodes{additions deletions}
                      pageInfo{hasNextPage endCursor}}}}}}}""",
                {"o": owner, "n": name, "uid": uid, "after": after},
            )["repository"]
            ref = r and r["defaultBranchRef"]
            if not ref:
                break
            hist = ref["target"]["history"]
            for n in hist["nodes"]:
                added += n["additions"]
                deleted += n["deletions"]
            if not hist["pageInfo"]["hasNextPage"]:
                break
            after = hist["pageInfo"]["endCursor"]

    stats = {
        "repos": u["repositories"]["totalCount"],
        "contributed": u["repositoriesContributedTo"]["totalCount"],
        "stars": stars,
        "commits": commits,
        "followers": u["followers"]["totalCount"],
        "loc_total": added - deleted,
        "loc_added": added,
        "loc_deleted": deleted,
    }
    (ROOT / "stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    print("stats updated:", stats)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # keep previous stats on any failure
        print("stats update failed, keeping previous values:", e)
