import os
import json
import requests


async def get_project_columns(project_id, headers):
    "get all columns for a target project"
    uri = f"https://api.github.com/projects/{project_id}/columns"
    response = requests.get(uri, headers=headers)
    return json.loads(response.content.decode())


async def get_column_cards(column_id, headers):
    "get all cards for the target column"
    uri = f"https://api.github.com/projects/columns/{column_id}/cards"
    response = requests.get(uri, headers=headers)
    return json.loads(response.content.decode())


async def get_org_projects(org_name, headers):
    "get all non-private projects for the organization; requires inertia-preview headers"
    uri = f"https://api.github.com/orgs/{org_name}/projects"
    response = requests.get(uri, headers=headers)
    return json.loads(response.content.decode())


async def get_project_cards(column_id, headers):
    "get all cards for a specific column"
    uri = f"https://api.github.com/projects/columns/{column_id}/cards"
    response = requests.get(uri, headers=headers)
    return json.loads(response.content.decode())


def update_sprint(event_data, headers):
    "update the current sprint in the config file"
    file_path = "Resources/config.json"
    new_proj_name = event_data.get("project", {}).get("name", None)
    with open(file_path, "r") as file_r:
        config_json = json.loads(file_r.read())
        config_json["projects"]["currentSprint"]["name"] = new_proj_name
        with open(file_path, "w+") as file_w:
            file_w.write(json.dumps(config_json))
