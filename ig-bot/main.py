import os
import sys
import json
import time
import asyncio
import dateutil.parser as dp

from aiohttp import web
from gidgethub import routing, sansio
from gidgethub import ValidationFailure

from static import graphql_endpoint
from settings import load_env_variables
from webhook_handlers import opened_issue
from util import token_expired, set_headers, get_installation_info, update_installations

# collection to store all authenticated tokens
# each token is associated with an installation
# { <installation_id>: { token: "", expires_at: "" } }
app_installations = dict()

router = routing.Router()

# get all environment variables
load_env_variables()
port = os.environ.get("PORT")


# region: events
# listen for events raised by the router
@router.register("issues", action="opened")
async def opened_issue_evt(event, token, *args, **kwargs):
    headers = set_headers(token)
    await opened_issue(event, headers)


# end region


async def main(request):
    body = await request.read()
    body_json = json.loads(body.decode())
    target_instl_id = body_json.get("installation").get("id")
    try:
        # pass the app's webhook secret to sansio for payload validation and create an event
        secret = os.environ.get("GITHUB_WEBHOOK_SECRET")
        event = sansio.Event.from_http(
            headers=request.headers, body=body, secret=secret
        )
    except ValidationFailure:
        # return Unauthorized if the request was not signed by GitHub
        return web.Response(status=401)
    if len(app_installations) == 0:
        # update all tokens if it is a first time start
        print("Initial start. Updating all tokens.")
        await update_installations(app_installations)
    elif target_instl_id not in app_installations or token_expired(
        target_instl_id, app_installations
    ):
        # update this particular installation's token if it has expired or the installation is new
        print(f"Updating/Adding token for app with ID: {target_instl_id}.")
        app_installations[target_instl_id] = await get_installation_info(
            target_instl_id
        )
    # get the installation's token
    token = app_installations[target_instl_id].get("token")
    # dispatch an event that contains the payload
    await router.dispatch(event, token=token)
    return web.Response(status=200)


if __name__ == "__main__":
    app = web.Application()
    app.router.add_post("/event-handler", main)
    if port is not None:
        port = int(port)
    web.run_app(app, port=port)
