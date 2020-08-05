import json
from dotenv import load_dotenv


def load_env_variables():
    "load all variables in the .env file"
    load_dotenv("./Resources/.env")


def get_orgname():
    config_json = read_config_json()
    return config_json.get("orgName", None)


def get_sprint_name():
    config_json = read_config_json()
    return config_json.get("projects", {}).get("currentSprint", {}).get("name", None)


def get_sprint_columns():
    config_json = read_config_json()
    return config_json.get("projects", {}).get("currentSprint", {}).get("columns", None)


def get_main_proj():
    config_json = read_config_json()
    return config_json.get("projects", {}).get("masterBacklog", None).get("name", None)


def read_project_columns(proj_name):
    config_json = read_config_json()
    projects = config_json.get("projects")
    proj_types = [name for name in projects]
    for p_type in proj_types:
        name = projects.get(p_type, {}).get("name", None)
        if name == proj_name:
            return projects.get(p_type, {}).get("columns", [])


def read_config_json():
    return json.loads(open("resources/config.json", "r").read())
