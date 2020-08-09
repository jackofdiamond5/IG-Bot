import re
import json
import requests

from settings import get_orgname, get_repositories
from labels import add_labels_to_labelable
from static import graphql_endpoint
from util import get_api_data, clean, build_payload
from projects import (
    get_master_backlog,
    select_project,
    add_issue_to_projects,
    get_project_data,
    get_projects_data
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
    post_labels_url = event_data.get("issue").get("labels_url")
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
    variables = json.dumps({"login": login, "name": repo_name})
    schema = open("Schemas/issues_for_repo.graphql", "r").read()
    payload = build_payload(schema, variables)
    return json.loads(
        requests.post(graphql_endpoint, payload, headers=headers).content.decode()
    )


async def get_issues_for_organization(login, headers):
    repositories = []
    for repo_name in get_repositories():
        repository = await get_issues_for_repo(login, repo_name, headers)
        repositories.append(
            repository.get("data")
            .get("organization")
            .get("repository")
            .get("issues")
            .get("nodes")
        )
    return repositories


def extract_issues_labels(repositories, login, headers):
    extracted = {}
    for issues in repositories:
        for issue in issues:
            issue_id = issue.get("id")
            if not issue_in_master_backlog(issue):
                extracted[issue_id] = ["Master Backlog"]
            if not issue_in_features_or_bugs_triage(issue):
                issue_labels = issue.get("labels").get("nodes")
                if issue_id not in extracted:
                    extracted[issue_id] = [select_project(issue_labels)]
                else:
                    extracted.get(issue_id).append(select_project(issue_labels))
    return extracted


def issue_in_master_backlog(issue):
    project_cards = issue.get("projectCards").get("nodes")
    for card in project_cards:
        if card.get("project").get("name") == "Master Backlog":
            return True
    return False


def issue_in_features_or_bugs_triage(issue):
    project_cards = issue.get("projectCards").get("nodes")
    for card in project_cards:
        card_name = card.get("project").get("name").strip()
        if card_name == "Features Triage" or card_name == "Bugs Triage":
            return True
    return False


async def try_add_issues_to_project(headers):
    master_backlog = await get_master_backlog(organization, headers)
    repositories = await get_issues_for_organization(organization, headers)
    extracted_issues = extract_issues_labels(repositories, organization, headers)

    if len(extracted_issues) > 0:
        for issue_id in extracted_issues:  # TODO write logic to add based on labels
            if extracted_issues[issue_id] is None:
                continue
            project_names = extracted_issues[issue_id]
            selected_projects = await get_projects_data(project_names, organization, headers)
            for selected_project in selected_projects:
                to_master_backlog = (
                    master_backlog.get("id")
                    if "Master Backlog" in extracted_issues[issue_id]
                    else None
                )
                await add_issue_to_projects(
                    issue_id,
                    list(
                        filter(None.__ne__, [to_master_backlog, selected_project.get("id")])
                    ),
                    headers,
                )
            # await add_labels_to_labelable([], issue_id, headers)
