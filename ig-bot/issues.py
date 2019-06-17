import re
import json
import requests

import util

from settings import get_orgname, get_sprint_name
from static import accept_headers
from projects import get_org_projects, get_project_columns, get_project_cards
from settings import get_main_proj, read_project_columns

# template string that is to be replaced with the Issue's or the PR's name or to be removed altogether
name_tmp = "{/name}"
number_tmp = "{/number}"


async def add_labels(event_data, headers, labels_to_add, *args, **kwargs):
    "add labels to an Issue"
    post_labels_url = event_data.get("issue", {}).get("labels_url", None)
    response = requests.post(post_labels_url.replace(
        name_tmp, ""), json.dumps(labels_to_add), headers=headers)
    return json.loads(response.content.decode())


async def remove_labels(event_data, headers):
    # valid format: @ig-bot remove label1, label2, labelN
    comment_body = event_data.get("comment", {}).get("body", None)
    labels_to_remove = util.digest_body(comment_body)
    # if the format of the inputted text does not match, skip
    if len(labels_to_remove) == 0:
        return
    lbls_url = event_data.get("issue", {}).get("labels_url", None)
    issue_labels = await util.get_api_data(lbls_url.replace(name_tmp, ""), headers)
    if len(issue_labels) == 0:
        return
    res = []
    for label in labels_to_remove:
        response = requests.delete(lbls_url.replace(
            name_tmp, f"/{label}"), headers=headers)
        res.append(json.loads(response.content.decode()))
    return res


async def add_to_org_project(event_data, headers):
    # GitHub requires a different Accept header for this endpoint
    headers["Accept"] = accept_headers["inertia_preview"]
    org_name = event_data.get("organization", {}).get("login", None)
    issue_id = event_data.get("issue", {}).get("id", None)
    if org_name == None or issue_id == None:
        return
    proj_name = get_main_proj()
    proj_id = await get_proj_id(proj_name, org_name, headers)
    columns_config = read_project_columns(proj_name)
    todo_col = columns_config[0]
    tgt_column = await get_target_column(proj_id, proj_name, todo_col, headers)
    # content_id and content_type must be specified - Issue or PR
    data = {"content_id": issue_id, "content_type": "Issue"}
    cards_url = tgt_column.get("cards_url")
    response = requests.post(cards_url, data=json.dumps(data), headers=headers)
    return json.loads(response.content.decode())


async def get_target_column(proj_id, proj_name, column_name, headers):
    proj_columns = await get_project_columns(proj_id, headers)
    tgt_column = next(
        iter((col for col in proj_columns if col.get("name").lower() == column_name.lower())), None)
    return tgt_column


async def get_proj_id(proj_name, org_name, headers):
    # a list of all projects in the organization
    projects = await get_org_projects(org_name, headers)
    tgt_project = next(
        iter((pr for pr in projects if pr.get("name", None) == proj_name)), None)
    proj_id = tgt_project.get("id", None)
    return proj_id


# TODO: Test
async def assign_teamlead(event_data, headers):
    issue_body = event_data.get("issue_body", None)
    target_control = match_control(issue_body)
    if target_control == None:
        return
    team = util.get_team_ownership(target_control)
    teamlead_login = team.get("lead", None)
    url = f"{event_data.get('url', None)}/assignees"
    headers["Accept"] = accept_headers["symmetra_preview"]
    response = requests.post(url, {"assignees": [teamlead_login]}, headers)
    return json.loads(response.content.decode())


# TODO: Test
# add a label that matches the control_name parameter
async def add_control_label(event_data, headers, control_name):
    repo_url = event_data.get("repository_url", None)
    lbls_url = f"{repo_url}/labels?page=1"
    # match the first label that corresponds to control_name
    t_label = await match_label(lbls_url, control_name, headers)
    if t_label == None:
        return
    labels_to_add = {"labels": [t_label]}
    return await add_labels(event_data, headers, labels_to_add)


async def match_label(labels_url, control_name, headers, page=1):
    "recursively search for a label that matches the control_name parameter"
    page_number = re.search(r"page=(\d+)?", labels_url).group(1)
    url = labels_url.replace(page_number, str(page))
    labels = await util.get_api_data(url, headers)
    for label in labels:
        # TODO: find a good way to unify the text from the input and the label name (NLP?)
        if util.clean(label["name"]) == util.clean(control_name):
            return label
        # if we are at the last label on the page and no match is found, request the next page of labels
        if labels.index(label) == len(labels) - 1:
            match = await match_label(url, control_name, headers, page + 1)
            return match
    return None


async def get_issues(headers):
    "get all issues for all repos that the installation has access to"
    all_issues = []
    all_repos = util.list_repositories(headers)
    for repo in all_repos:
        issues_url = repo.get("issues_url", None).replace(number_tmp, "")
        response = requests.get(issues_url, headers=headers)
        # Github returns an array of issues per repository
        repo_issues = json.loads(response.content.decode())
        for issue in repo_issues:
            all_issues.append(issue)
    return all_issues


async def move_issue(to_column, issue_card, col_id, headers):
    card_id = issue_card.get("id", None)
    data = {"position": "top", "column_id": col_id}
    uri = f"https://api.github.com/projects/columns/cards/{card_id}/moves"
    response = requests.post(uri, data=json.dumps(data), headers=headers)
    return json.loads(response.content.decode())


# TODO
async def issue_misplaced(issue):
    NotImplemented


# get the control that is referenced in the issue's body (if any)
def match_control(issue_body):
    pattern = r"control: \w+(((-|\s)\w+){0,})(\r|\n)"
    # case insensitve search
    match = re.search(pattern, issue_body, re.I).group()
    clean = util.clean(match)
    # valid form 'control: drop-down'
    args = clean.split(':')
    m_control = args[1].strip().replace(clean, "")
    return m_control
