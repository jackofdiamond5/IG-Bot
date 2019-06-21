import json
import requests

import util
import issues
import projects as proj
import pull_requests as pr

from project_cards import try_move_card

# handler functions for webhook events
# payload = event.data


# region Projects:
async def created_project(event, headers):
    proj.update_sprint(event.data, headers)
# endregion


# region Issues:
async def labeled_issue(event, headers):
    # print(event.data)
    await try_move_card(event.data, headers)


async def unlabeled_issue(event, headers):
    print("someone unlabeled your issue, boi")


async def opened_issue(event, headers):
    config = json.loads(open("Resources/config.json").read())
    issue_labels = {"labels": config.get("newIssueLabels", None)}
    await issues.add_labels(event.data, headers, labels_to_add=issue_labels)
    await issues.add_to_org_project(event.data, headers)


async def posted_comment_issue(event, headers):
    await issues.remove_labels(event.data, headers)
# end region


# region PRs:
async def opened_pr(event, headers):
    await pr.add_labels(event.data, headers)

async def pr_set_to_ready(event, headers):
    await pr.add_labels(event.data, headers)
# end region
