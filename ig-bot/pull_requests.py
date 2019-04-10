import json
import requests
import dateutil.parser as dp

from datetime import datetime

from issues import add_labels as add_labels_to_pr


async def add_labels(event_data, headers):
    config = json.loads(open("Resources/config.json").read())
    labels_to_add = json.dumps({"labels": config.get("newPrLabels", None)})
    if (not is_pr(event_data)):
        return
    issue_url = event_data.get("pull_request", {}).get("issue_url", None)
    # treat this PR as an Issue
    pr_issue = await get_pr_issue(issue_url, headers)
    return await add_labels_to_pr({"issue": pr_issue}, headers, labels_to_add=labels_to_add)


# get the issue equivalent of the PR - for GitHub each PR is also an issue
async def get_pr_issue(issue_url, headers):
    # i.e. each PR can be represented as an Issue
    # this does NOT return the Issue that is referenced in the PR
    issue_body = requests.get(issue_url, params=None, headers=headers)
    return json.loads(issue_body.content.decode())


def is_pr(payload):
    # determines if the Issue is a PR
    return "pull_request" in payload
