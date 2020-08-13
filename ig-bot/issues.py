import re
import json
import requests

from settings import get_orgname, get_repositories
from labels import add_labels_to_labelable, get_label_by_name
from static import graphql_endpoint, labels_to_skip
from util import get_api_data, clean, build_payload
from projects import (
    get_master_backlog,
    select_project,
    add_issue_to_projects,
    get_project_data,
    get_projects_data,
)

# template string that is to be replaced with the Issue's or the PR's name or to be removed altogether
name_tmp = "{/name}"
organization = get_orgname()


async def get_issue_for_repository(login, repo_name, issue_number, headers):
    schema = open("Schemas/get_issue_for_repo.graphql", "r").read()
    variables = json.dumps({
        "login": login,
        "repo_name": repo_name,
        "issue_number": issue_number
    })
    payload = build_payload(schema, variables)
    response = requests.post(graphql_endpoint, payload,
                             headers=headers).content.decode()
    return json.loads(response)


async def add_to_projects(event_data, headers):
    "add an issue to predefined Github projects"
    issue = event_data.get("issue")
    issue_id = issue.get("node_id")
    issue_labels = issue.get("labels")
    issue_number = issue.get("number")
    repo_name = event_data.get("repository").get("name")
    response = await get_issue_for_repository(organization, repo_name,
                                              issue_number, headers)
    target_projects_ids = get_projects_for_issue(
        response.get("data").get("organization").get("repository").get(
            "issue"))
    master_backlog = await get_master_backlog(organization, headers)
    selected_project_id = await select_project(issue_labels, organization, headers)
    target_projects_ids.extend([master_backlog.get("id"), selected_project_id])
    await add_issue_to_projects(
        issue_id,
        list(filter(None.__ne__, target_projects_ids)),
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
        requests.post(graphql_endpoint, payload,
                      headers=headers).content.decode())


async def get_issues_for_organization(login, headers):
    "returns a collection of repositories that contain all issues for each repository"
    repositories = {}
    repo_names = get_repositories()
    for repo_name in repo_names:
        repository = await get_issues_for_repo(login, repo_name, headers)
        repositories[repo_name] = (repository.get("data").get(
            "organization").get("repository").get("issues").get("nodes"))
    return repositories


def get_projects_for_issue(issue):
    project_cards = issue.get("projectCards").get("nodes")
    ids = []
    for card in project_cards:
        ids.append(card.get("project").get("id"))
    return ids


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
    print("Including issues to projects.")
    master_backlog = await get_master_backlog(organization, headers)
    repositories = await get_issues_for_organization(organization, headers)
    for repo_name in repositories:
        issues = repositories[repo_name]
        for issue in issues:
            issue_id = issue.get("id")
            issue_labels = issue.get("labels").get("nodes")
            if issue_in_master_backlog(
                    issue) and issue_in_features_or_bugs_triage(issue):
                continue
            issue_projects_ids = get_projects_for_issue(issue)
            selected_proj_id = await select_project(issue_labels, organization,
                                                    headers)
            master_backlog_id = (master_backlog.get("id")
                                 if master_backlog.get("id")
                                 not in issue_projects_ids else None)
            issue_projects_ids.extend([selected_proj_id, master_backlog_id])
            await add_issue_to_projects(
                issue_id, list(filter(None.__ne__, issue_projects_ids)),
                headers)


async def try_add_labels_to_issues(label_name, headers):
    print("Adding labels.")
    repositories = await get_issues_for_organization(organization, headers)
    all_labels = await get_label_by_name(label_name, organization, headers)
    for repo_name in repositories:
        issues = repositories[repo_name]
        for issue in issues:
            issue_labels = issue.get("labels").get("nodes")
            labels_in_issue = [
                label.get("name").strip() for label in issue_labels
            ]
            if not any(name in labels_in_issue for name in labels_to_skip):
                await try_add_labels_to_issue(repo_name, issue, all_labels,
                                              headers)


async def try_add_labels_to_issue(repo_name, issue, labels_data, headers):
    repositories = (labels_data.get("data").get("organization").get(
        "repositories").get("nodes"))
    label_id = [
        repositories[i].get("label").get("id")
        for i in range(len(repositories))
        if repositories[i].get("name").strip() == repo_name
    ]
    await add_labels_to_labelable(label_id, issue.get("id"), headers)
