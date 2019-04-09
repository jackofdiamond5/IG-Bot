import os
import sys
import json
import time
import dateutil.parser as dp

from aiohttp import web
from gidgethub import routing, sansio
from gidgethub import ValidationFailure
from gidgethub import aiohttp as gh_aiohttp
from datetime import datetime, timedelta

import util
import settings
import pull_requests as pr
import webhook_handlers as wh


# collection to store all authenticated tokens
# each token is associated with an installation
# { <installation_id>: { token: "", expires_at: "" } }
app_intallations = dict()

router = routing.Router()

# get all environment variables
settings.load_env_variables()
port = os.environ.get("PORT")


# region: events
# listen for events raised by the router
@router.register("issues", action="labeled")
async def labeled_issue_evt(event, token, *args, **kwargs):
    headers = {"Authorization": f"token {token}",
               "Accept": "application/vnd.github.machine-man-preview+json"}
    await wh.labeled_issue(event, headers)


@router.register("issues", action="unlabeled")
async def unlabeled_issue_evt(event, token, *args, **kwargs):
    headers = {"Authorization": f"token {token}",
               "Accept": "application/vnd.github.machine-man-preview+json"}
    await wh.unlabeled_issue(event, headers)


@router.register("issues", action="opened")
async def opened_issue_evt(event, token, *args, **kwargs):
    headers = {"Authorization": f"token {token}",
               "Accept": "application/vnd.github.machine-man-preview+json"}
    await wh.opened_issue(event, headers)


@router.register("issue_comment", action="created")
async def posted_comment_issue_evt(event, token, *args, **kwargs):
    headers = {"Authorization": f"token {token}",
               "Accept": "application/vnd.github.machine-man-preview+json"}
    await wh.posted_comment_issue(event, headers)


@router.register("pull_request", action="opened")
async def opened_pr_evt(event, token, *args, **kwargs):
    # since GitHub's PRs are also Issues the Accept header remains the same
    headers = {"Authorization": f"token {token}",
               "Accept": "application/vnd.github.machine-man-preview+json"}
    await wh.opened_pr(event, headers)
# end region


async def main(request):
    body = await request.read()
    target_instl_id = util.get_app_installation_id(json.loads(body.decode()))
    try:
        # pass the app's webhook secret to sansio for payload validation and create an event
        secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
        event = sansio.Event.from_http(
            headers=request.headers, body=body, secret=secret)
    except ValidationFailure:
        # return Unauthorized if the request was not signed by GitHub
        return web.Response(status=401)
    if len(app_intallations) == 0:
        # update all tokens if it is a first time start
        print("Initial start. Updating all tokens.")
        await util.update_installations(app_intallations)
    elif target_instl_id not in app_intallations or util.token_expired(target_instl_id, app_intallations):
        # update this particular installation's token if it has expired or the installation is new
        print(f"Updating/Adding token for app with ID: {target_instl_id}.")
        app_intallations[target_instl_id] = await util.get_installation_info(target_instl_id)
    # get the installation's token
    token = app_intallations[target_instl_id].get("token", None)
    # dispatch an event that contains the payload
    await router.dispatch(event, token=token)
    return web.Response(status=200)


if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("/event-handler", main)
    if port is not None:
        port = int(port)
    web.run_app(app, port=port)
