import re
import json
import schedule
import requests
import dateutil.parser as dp

from datetime import datetime
from static import accept_headers
from settings import get_sprint_columns
from issues import issue_misplaced, move_issue, get_issues

import authenticate as auth


async def get_api_data(uri, headers):
    # authorized get request
    response = requests.get(uri, headers=headers)
    return json.loads(response.content.decode())


# get all app installations
async def update_installations(app_intallations):
    response = await auth.find_all_installations()
    res_body = json.loads(response.get("body", None))
    await update_tokens(res_body, app_intallations)


# update the tokens for all installations
async def update_tokens(installations, app_intallations):
    for installation in installations:
        installation_id = installation.get("id", None)
        app_intallations[installation_id] = await get_installation_info(
            installation_id)
    return app_intallations


# get updated data for an installation
async def get_installation_info(installation_id):
    auth_res = await auth.auth_installation(installation_id)
    res_body = json.loads(auth_res.get("body", {}))
    return res_body


# TODO: Test
# moves issues that have "in-development" label to "In Progress" if they are in "To do" column of the current sprint
async def move_issues(app_installations):
    for instl in app_installations:
        token = app_installations[instl].get("token", None)
        if (token == None):
            return
        headers = {"Authorization": f"token {token}",
                   "Accept": accept_headers["inertia_preview"]}
        all_issues = await get_issues(headers)
        for issue in all_issues:
            if issue_misplaced(issue):
                await move_issue("In Progress", issue, headers)


# search for the team which owns the passed in control
def get_team_ownership(control_name):
    config_json = json.loads(open("config.json", "r").read())
    teams = config_json.get("teams", {})
    for team in teams:
        team_ownership = teams[team].get("ownership", [])
        if control_name in team_ownership:
            return teams[team]
    return None


# strip the match of new lines, spaces, and dashes
def clean(text):
    return re.sub(r"((\n|\r)|[- ]+)", "", text)


# get the labels that need to be removed
def digest_body(body):
    body_p = body.split("remove")
    if len(body_p) != 2:
        return []
    # beggining of line or space + @ig-bot + space or end of line
    pattern = r"(^|\s)@ig-bot($|\s)"
    # case insensitive search
    if re.search(pattern, body_p[0], re.I | re.M) == None:
        return []
    args = body_p[1]
    selected_labels = []
    # args.Split(',').Select(arg => arg.Trim()).ToList()
    for label in list(arg.strip() for arg in args.split(',')):
        selected_labels.append(label)
    return selected_labels


def token_expired(target_instl_id, app_intallations):
    # expires_at shows when the token will expire (UTC+1)
    expires_at = app_intallations[target_instl_id].get("expires_at", None)
    # convert the date to local datetime and return if it has expired
    parsed = dp.parse(expires_at).astimezone().replace(tzinfo=None)
    return parsed <= datetime.now()


def validate_token(token):
    if (type(token) != str):
        raise ValueError(
            f"Expected type 'str' for argument 'token'. Given value is: {token}.")
