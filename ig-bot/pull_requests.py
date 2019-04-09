import json
import requests
import dateutil.parser as dp

from datetime import datetime

import issues

# template string that is to be replaced with the Issue's or the PR's name or to be removed altogether
str_tmp = "{/name}"
labels_to_add = {"labels": ["status: awaiting-test"]}
# GitHub requres a different Accept header for this endpoint
# with this accept header the draft state of the PR can be seen
accept_h = "application/vnd.github.shadow-cat-preview"


async def add_labels(event_data, headers):
    if (not is_pr(event_data)):
        return
    issue_url = event_data.get("pull_request", {}).get("issue_url", None)
    # treat this PR as an Issue
    pr_issue = await get_pr_issue(issue_url, headers)
    return await issues.add_labels({"issue": pr_issue}, headers)


async def get_pr_issue(issue_url, headers):
    # get the issue equivalent of the PR - for GitHub each PR is also an issue
    # i.e. each PR can be represented as an Issue
    # this does NOT return the Issue that is referenced in the PR
    issue_body = requests.get(issue_url, params=None, headers=headers)
    return json.loads(issue_body.content.decode())


def is_pr(payload):
    # determines if the Issue is a PR
    return "pull_request" in payload
