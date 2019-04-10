import os
import json


# update the current sprint in the config file
def update_sprint(event_data, headers):
    file_path = "Resources/config.json"
    new_proj_name = event_data.get("project", {}).get("name", None)
    with open(file_path, "r") as file_r:
        config_json = json.loads(file_r.read())
        config_json["projects"]["currentSprint"]["name"] = new_proj_name
        with open(file_path, "w+") as file_w:
            file_w.write(json.dumps(config_json))
