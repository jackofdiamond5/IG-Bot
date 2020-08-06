import re
import json
import requests

from settings import get_orgname
from util import get_api_data, clean
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

