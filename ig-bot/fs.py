def get_orgname(config_json):
    return config_json.get("orgName", None)


def get_sprint(config_json):
    return config_json.get("projects", {}).get("currentSprint", {}).get("name", None)


def get_main_proj(config_json):
    return config_json.get("projects", {}).get("masterBacklog", None).get("name", None)


def get_proj_columns(config_json, proj_name):
    projects = config_json.get("projects")
    proj_types = list((name for name in projects))
    for p_type in proj_types:
        name = projects.get(p_type, {}).get("name", None)
        if name == proj_name:
            # the first column should be "Todo"
            # the second column should be "In progress"
            # the third column should be "Done"
            return projects.get(p_type, {}).get("columns", [])
