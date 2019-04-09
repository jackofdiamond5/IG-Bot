import re
import json
import requests

import fs
import util

# template string that is to be replaced with the Issue's or the PR's name or to be removed altogether
str_tmp = "{/name}"
labels_to_add = {"labels": ["status: in review"]}


async def add_labels(event_data, headers):
    # add labels to an Issue
    post_labels_url = event_data.get("issue", {}).get("labels_url", None)
    response = requests.post(post_labels_url.replace(
        str_tmp, ""), json.dumps(labels_to_add), headers=headers)
    return json.loads(response.content.decode())


async def remove_labels(event_data, headers):
    # valid format: @ig-bot remove label1, label2, labelN
    comment_body = event_data.get("comment", {}).get("body", None)
    labels_to_remove = util.digest_body(comment_body)
    # if the format of the inputted text does not match, skip
    if (len(labels_to_remove) == 0):
        return
    lbls_url = event_data.get("issue", {}).get("labels_url", None)
    issue_labels = await util.get_labels(lbls_url.replace(str_tmp, ""))
    if len(issue_labels) == 0:
        return
    res = []
    for label in labels_to_remove:
        response = requests.delete(lbls_url.replace(
            str_tmp, f"/{label}"), headers=headers)
        res.append(json.loads(response.content.decode()))
    return res


async def add_to_org_project(event_data, headers):
    # GitHub requires a different Accept header for this endpoint
    headers["Accept"] = "application/vnd.github.inertia-preview+json"
    org_name = event_data.get("organization", {}).get("login", None)
    issue_id = event_data.get("issue", {}).get("id", None)
    if org_name == None or issue_id == None:
        return
    org_projects_url = f"https://api.github.com/orgs/{org_name}/projects"
    # a list of all projects in the organization
    projects = await util.get_api_data(org_projects_url, headers)
    config = open("resources/config.json", "r")
    config_json = json.loads(config.read())
    proj_name = fs.get_main_proj(config_json)
    tgt_project = next(
        iter((pr for pr in projects if pr.get("name", None) == proj_name)), None)
    proj_columns_url = tgt_project.get("columns_url", None)
    if proj_columns_url == None:
        return
    proj_columns = await util.get_api_data(proj_columns_url, headers)
    columns = fs.get_proj_columns(config_json, proj_name)
    tgt_column = next(
        iter((col for col in proj_columns if col.get("name", None) == columns[0])), None)
    # content_id and content_type must be specified - Issue or PR
    data = {"content_id": issue_id, "content_type": "Issue"}
    col_url = tgt_column.get("cards_url")
    response = requests.post(col_url, data=json.dumps(data), headers=headers)
    return json.loads(response.content.decode())


async def assign_teamlead(event_data, headers):
    issue_body = event_data.get("issue_body", None)
    target_control = match_control(issue_body)
    if (target_control == None):
        return

    NotImplemented


async def get_controls_labels(event_data, headers):
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
