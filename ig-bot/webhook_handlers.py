import json

from issues import add_labels, add_to_projects, get_labels_for_issue, get_issue_for_repository
from projects import add_issue_to_projects, select_project
from settings import get_orgname
from util import switch_label
from static import target_labels

organization = get_orgname()


# handler functions for webhook events
# payload = event.data

# region Issues:
async def opened_issue(event, headers):
    "react to events for newly-opened issues"
    config = json.loads(open("Resources/config.json").read())
    issue_labels = {"labels": config.get("newIssueLabels")}
    await add_labels(event.data, headers, labels_to_add=issue_labels)
    await add_to_projects(event.data, headers)


async def labelled_issue(event, headers):
    issue = event.data.get("issue")
    issue_id = issue.get("node_id")
    label = event.data.get("label")
    issue_number = issue.get("number")
    repo_name = event.data.get("repository").get("name")
    added_label = label.get("name")
    if added_label not in target_labels:
        return
    issue_labels = await get_labels_for_issue(repo_name, issue_number, headers)
    current_projects = (await get_issue_for_repository(
        organization, repo_name, issue_number,
        headers)).get('data').get("organization").get("repository").get(
            "issue").get("projectCards").get("nodes")
    target_project = await select_project(issue_labels, organization, headers,
                                          added_label)
    projects_to_add = [
        current_projects[i].get("project").get("id")
        for i in range(len(current_projects))
    ]
    projects_to_add.append(target_project)
    await add_issue_to_projects(issue_id, projects_to_add, headers)


# end region