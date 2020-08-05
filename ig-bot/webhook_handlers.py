import json
from issues import add_labels, add_to_projects

# handler functions for webhook events
# payload = event.data


# region Issues:
async def opened_issue(event, headers):
    config = json.loads(open("Resources/config.json").read())
    issue_labels = {"labels": config.get("newIssueLabels", None)}
    await add_labels(event.data, headers, labels_to_add=issue_labels)
    await add_to_projects(event.data, headers)
