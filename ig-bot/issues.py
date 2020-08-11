import re
import json
import requests

from settings import get_orgname, get_repositories
from labels import add_labels_to_labelable, get_label_by_name
from static import graphql_endpoint
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
    "returns a collection of repositories that contain all issues for each repository"
    repositories = {}
    repo_names = get_repositories()
    for repo_name in repo_names:
        repository = await get_issues_for_repo(login, repo_name, headers)
        repositories[repo_name] = (
            repository.get("data")
            .get("organization")
            .get("repository")
            .get("issues")
            .get("nodes")
        )
    return repositories


def extract_issues_projects(repositories, login, headers):
    "gets all project names that are associated with a specific issue"
    extracted = {}
    for repo_name in repositories:
        issues = repositories[repo_name]
        for issue in issues:
            issue_id = issue.get("id")
            issue_labels = issue.get("labels").get("nodes")
            if issue_in_master_backlog(issue) and issue_in_features_or_bugs_triage(
                issue
            ):
                continue
            issue_projects = get_projects_for_issue(issue)
            project_names = [
                "Master Backlog",
                select_project(issue_labels),
            ]
            if issue_projects is not None:
                project_names = list(set(project_names + issue_projects))
            extracted[issue_id] = project_names
    return extracted


def get_projects_for_issue(issue):
    project_cards = issue.get("projectCards").get("nodes")
    names = []
    for card in project_cards:
        names.append(card.get("project").get("name"))
    return names


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
    extracted_issues = extract_issues_projects(repositories, organization, headers)
    if len(extracted_issues) <= 0:
        return
    for issue_id in extracted_issues:
        project_names = extracted_issues[issue_id]
        if project_names is None:
            continue
        selected_projects = await get_projects_data(
            project_names, organization, headers
        )
        master_backlog_id = (
            master_backlog.get("id")
            if "Master Backlog" in extracted_issues[issue_id]
            else None
        )
        ids = [sp.get("id") for sp in selected_projects]
        ids.append(master_backlog_id)
        await add_issue_to_projects(issue_id, list(filter(None.__ne__, ids)), headers)


async def try_add_labels_to_issues(label_name, headers):
    print("Adding labels.")
    repositories = await get_issues_for_organization(organization, headers)
    all_labels = await get_label_by_name(label_name, organization, headers)
    for repo_name in repositories:
        issues = repositories[repo_name]
        for issue in issues:
            issue_labels = issue.get("labels").get("nodes")
            labels_to_skip = [
                label.get("name").strip()
                for label in issue_labels
                if label.get("name").strip() == label_name
            ]
            if len(labels_to_skip) == 0:
                await try_add_labels_to_issue(repo_name, issue, all_labels, headers)


async def try_add_labels_to_issue(repo_name, issue, labels_data, headers):
    repositories = (
        labels_data.get("data").get("organization").get("repositories").get("nodes")
    )
    label_id = [
        repositories[i].get("label").get("id")
        for i in range(len(repositories))
        if repositories[i].get("name").strip() == repo_name
    ]
    await add_labels_to_labelable(label_id, issue.get("id"), headers)
