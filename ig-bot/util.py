import re
import json
import requests
import dateutil.parser as dp
import authenticate as auth

from datetime import datetime


async def get_api_data(uri, headers):
    "authorized get request"
    response = requests.get(uri, headers=headers)
    return json.loads(response.content.decode())


async def update_installations(app_installations):
    "get all app installations"
    response = await auth.find_all_installations()
    res_body = json.loads(response.get("body"))
    await update_tokens(res_body, app_installations)


async def update_tokens(installations, app_installations):
    "update the tokens for all installations"
    for installation in installations:
        installation_id = installation.get("id")
        app_installations[installation_id] = await get_installation_info(
            installation_id)
    return app_installations


async def get_installation_info(installation_id):
    "get updated data for an installation"
    auth_res = await auth.auth_installation(installation_id)
    res_body = json.loads(auth_res.get("body", {}))
    return res_body


async def list_repositories(headers):
    "list all repositories that the current installation has access to"
    uri = "https://api.github.com/installation/repositories"
    response = requests.get(uri, data=None, headers=headers)
    # status is OK if the request passed authentication
    return {
        "status": response.reason,
        "body": json.loads(response.content.decode())
    }


def clean(text):
    "strip the match of new lines, spaces, and dashes"
    return re.sub(r"((\n|\r)|[- ]+)", "", text)


def digest_body(body):
    "get the labels that need to be removed"
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
    for label in list(arg.strip() for arg in args.split(",")):
        selected_labels.append(label)
    return selected_labels


def token_expired(target_instl_id, app_installations):
    "returns if the token for the specific installation has expired"
    # expires_at shows when the token will expire (UTC+1)
    expires_at = app_installations[target_instl_id].get("expires_at")
    # convert the date to local datetime and return if it has expired
    parsed = dp.parse(expires_at).astimezone().replace(tzinfo=None)
    return parsed <= datetime.now()


def set_headers(token, accept=None, bearer=False):
    "set the headers for an authorized request to Github"
    if bearer:
        return {"Authorization": f"Bearer {token}", "Accept": accept}
    return {"Authorization": f"token {token}", "Accept": accept}


def build_payload(schema, variables):
    "build a graphql payload that is to be sent to Github"
    newLine = "\n"
    return json.dumps({
        "query": schema.replace(newLine, ""),
        "variables": variables.replace(newLine, ""),
    })


def switch_label(value):
    return {"bug": "Bugs Triage", "feature-request": "Features Triage"}[value]
