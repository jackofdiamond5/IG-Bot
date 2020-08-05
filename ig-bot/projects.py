import json
import requests

from util import build_payload
from static import graphql_endpoint
from settings import get_orgname

organization = get_orgname()


async def add_issue_to_projects(issue_id, project_ids, headers):
    variables = (
        "{"
        + f'"issue_id": "{issue_id}", "project_ids": {json.dumps(project_ids)}'
        + "}"
    )
    schema = open("Schemas/add_to_project.graphql", "r").read()
    payload = build_payload(schema, variables)
    response = requests.post(graphql_endpoint, payload, headers=headers)
    return json.loads(response.content.decode())


async def get_project_columns(target_project, headers):
    response = await get_project_data(target_project, organization, headers)
    projects = response.get("data").get("organization").get("projects").get("nodes")
    return projects[0].get("columns").get("nodes")


async def get_master_backlog(login, headers):
    return await get_project_data("Master Backlog", login, headers)


def select_project(issue_labels):
    names = [
        issue
        for issue in issue_labels
        if issue.get("name") == "bug" or issue.get("name") == "feature-request"
    ]
    project = {"bug": "Bugs Triage", "feature-request": "Features Triage"}
    label_name = names[0].get("name")
    if label_name not in project.keys():
        return None
    return project[label_name]


async def get_project_data(project_name, login, headers):
    variables = "{" + f'"projectName": "{project_name}", "login": "{login}"' + "}"
    schema = open("Schemas/project_data.graphql", "r").read()
    payload = build_payload(schema, variables)
    response = requests.post(graphql_endpoint, payload, headers=headers)
    response_json = json.loads(response.content.decode())
    return response_json.get("data").get("organization").get("projects").get("nodes")[0]
