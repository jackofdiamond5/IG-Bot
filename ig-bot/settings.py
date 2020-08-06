import json
from dotenv import load_dotenv


def load_env_variables():
    "load all variables in the .env file"
    load_dotenv("./Resources/.env")


def get_orgname():
    "returns the name of the organization in config.json"
    config_json = read_config_json()
    return config_json.get("orgName")


def get_main_proj():
    "returns the name of the organization's main project"
    config_json = read_config_json()
    return config_json.get("projects", {}).get("masterBacklog").get("name")


def read_project_columns(proj_name):
    "returns a collection of all columns for the specified project name"
    config_json = read_config_json()
    projects = config_json.get("projects")
    proj_types = [name for name in projects]
    for p_type in proj_types:
        name = projects.get(p_type, {}).get("name")
        if name == proj_name:
            return projects.get(p_type, {}).get("columns", [])


def get_repositories():
    config_json = read_config_json()
    return config_json.get("repositories")


def read_config_json():
    "returns loaded json of config.json"
    return json.loads(open("resources/config.json", "r").read())
