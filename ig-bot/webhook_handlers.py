import json
import requests

import util
import issues
import pull_requests as pr

# handler functions for webhook events
# payload = event.data


# region Issues:
async def labeled_issue(event, headers):
    print("someone labeled your issue, boi")


async def unlabeled_issue(event, headers):
    print("someone unlabeled your issue, boi")


async def opened_issue(event, headers):
    await issues.add_labels(event.data, headers)
    await issues.add_to_org_project(event.data, headers)


async def posted_comment_issue(event, headers):
    await issues.remove_labels(event.data, headers)
# end region


# region PRs:
async def opened_pr(event, headers):
    await pr.add_labels(event.data, headers)
# end region
