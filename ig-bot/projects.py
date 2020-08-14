import json
import requests

from util import build_payload, switch_label
from static import graphql_endpoint, target_labels
from settings import get_orgname

organization = get_orgname()


async def add_issue_to_projects(issue_id, project_ids, headers):
    "send a graphql mutation to Github to move an issue to specific projects"
    variables = json.dumps({"issue_id": issue_id, "project_ids": project_ids})
    schema = open("Schemas/add_to_project.graphql", "r").read()
    payload = build_payload(schema, variables)
    response = requests.post(graphql_endpoint, payload, headers=headers)
    return json.loads(response.content.decode())


async def get_project_columns(target_project, headers):
    "get all columns of a specific project"
    response = await get_project_data(target_project, organization, headers)
    projects = response.get("data").get("organization").get("projects").get(
        "nodes")
    return projects[0].get("columns").get("nodes")


async def get_master_backlog(login, headers):
    "returns a dict that contains data based on project_data.graphql"
    return await get_project_data("Master Backlog", login, headers)


async def select_project(issue_labels, login, headers, *args):
    "selects a project between 'Bugs Triage' and 'Features Triage'"
    labels = [
        label for label in issue_labels if label.get("name") in target_labels
    ]
    if len(args) > 0:
        label_name = [
            label.get("name") for label in labels if label.get("name") in args
        ][0]
    else:
        label_name = labels[0].get("name") if len(labels) > 0 else None
    if label_name is None:
        return None
    project = switch_label(label_name)
    project_data = await get_project_data(project, login, headers)
    return project_data.get("id")


async def get_project_data(project_name, login, headers):
    "returns a project dict in the format specified in project_data.graphql"
    variables = json.dumps({"projectName": project_name, "login": login})
    schema = open("Schemas/project_data.graphql", "r").read()
    payload = build_payload(schema, variables)
    response = requests.post(graphql_endpoint, payload, headers=headers)
    response_json = json.loads(response.content.decode())
    nodes = response_json.get("data").get("organization").get("projects").get(
        "nodes")
    # returns a project object { name: string, id: string, columns:[{ name, id, url }] }
    return nodes[0] if len(nodes) > 0 else None


async def get_projects_data(projects_names, login, headers):
    "returns a dict with all of the projects names, ids and columns"
    projects_data = []
    for project_name in projects_names:
        if project_name is None:
            continue
        result = await get_project_data(project_name, login, headers)
        if result is not None:
            projects_data.append(result)
    return projects_data
