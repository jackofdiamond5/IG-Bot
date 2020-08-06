import re
import json
import requests

from settings import get_orgname, get_repositories
from static import graphql_endpoint
from util import get_api_data, clean, build_payload
from projects import (
    get_master_backlog,
    select_project,
    add_issue_to_projects,
    get_project_data,
)


# template string that is to be replaced with the Issue's or the PR's name or to be removed altogether
name_tmp = "{/name}"
organization = get_orgname()


async def add_to_projects(event_data, headers):
    "add an issue to predefined Github projects"
    issue = event_data.get("issue")
    issue_id = issue.get("node_id")
    issue_labels = issue.get("labels")
    master_backlog = await get_master_backlog(organization, headers)
    project_name = select_project(issue_labels)
    target_project, target_project_id = None, None
    if project_name is not None:
        target_project = await get_project_data(project_name, organization, headers)
    if target_project is not None:
        target_project_id = target_project.get("id")
    await add_issue_to_projects(
        issue_id,
        list(filter(None.__ne__, [master_backlog.get("id"), target_project_id])),
        headers,
    )


async def add_labels(event_data, headers, labels_to_add, *args, **kwargs):
    "add labels to an Issue"
    post_labels_url = event_data.get("issue", {}).get("labels_url")
    response = requests.post(
        post_labels_url.replace(name_tmp, ""),
        json.dumps(labels_to_add),
        headers=headers,
    )
    return json.loads(response.content.decode())


async def match_label(labels_url, control_name, headers, page=1):
    "recursively search for a label that matches the control_name parameter"
    page_number = re.search(r"page=(\d+)?", labels_url).group(1)
    url = labels_url.replace(page_number, str(page))
    labels = await get_api_data(url, headers)
    for label in labels:
        if clean(label["name"]) == clean(control_name):
            return label
        # if we are at the last label on the page and no match is found, request the next page of labels
        if labels.index(label) == len(labels) - 1:
            match = await match_label(url, control_name, headers, page + 1)
            return match
    return None


async def get_issues_for_repo(login, repo_name, headers):
    variables = "{" + f'"login": "{login}"' + f', "name": "{repo_name}"' + "}"
    schema = open("Schemas/issues_for_repo.graphql", "r").read()
    payload = build_payload(schema, variables)
    print(payload)
    return json.loads(
        requests.post(graphql_endpoint, payload, headers=headers).content.decode()
    )


async def find_issues_without_project(login, headers):
    issues_without_project = []
    for repo_name in get_repositories():
        response = await get_issues_for_repo(login, repo_name, headers)
        issues = (
            response.get("data")
            .get("organization")
            .get("repository")
            .get("issues")
            .get("nodes")
        )
        for issue in issues:
            if len(issue.get("projectCards").get("nodes")) == 0:
                issues_without_project.append(issue.get("id"))
    return issues_without_project


async def try_add_issues_to_project(headers):
    login = get_orgname()
    master_backlog = await get_master_backlog(login, headers)
    issues_without_project = await find_issues_without_project(login, headers)
    if len(issues_without_project) > 0:
        for issue_id in issues_without_project:
            await add_issue_to_projects(issue_id, [master_backlog.get("id")], headers)
