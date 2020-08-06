import os
import jwt
import hmac
import time
import json
import util
import requests

from hashlib import sha1
from static import accept_headers
from settings import load_env_variables

load_env_variables()


def generate_jwt_payload():
    "generate payload for jwt encoding"
    gh_app_id = os.getenv("GITHUB_APP_IDENTIFIER")
    current_time = int(time.time())
    return {"iat": current_time, "exp": current_time + (10 * 60), "iss": gh_app_id}


def get_jwt_token_bytes():
    """creates a jwt token using the RS256 algorithm
    \n it will be sent to GitHub to verify the app"""
    gh_app_key = os.getenv("PRIVATE_KEY")
    payload = generate_jwt_payload()
    return jwt.encode(payload, gh_app_key, "RS256")


# region: custom payload validation
def sign_request(body_b):
    "generate a hexadecimal key for GitHub's webhook"
    # body_b is the body of the webhook response obj
    gh_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    hashed = hmac.new(gh_secret.encode(), body_b, sha1)
    return "sha1=" + hashed.hexdigest()


def verify_signature(digest_1, digest_2):
    # GitHub sends a hashed header (X-HUB-SIGNATURE) which is to be compared to the locally generated one
    # verify that a request is received from GitHub
    return hmac.compare_digest(digest_1, digest_2)


# end region


async def auth_app():
    "authenticate as a GitHub application to access high level API"
    token = get_jwt_token_bytes().decode()
    uri = "https://api.github.com/app"
    headers = util.set_headers(token, accept_headers["machine_man_preview"], True)
    response = requests.get(uri, params=None, headers=headers)
    # status is OK if the app is authenticated and Not Found if something went wrong
    # return the token and the response body
    # the token may be needed for additional authentication
    return {"jwt": token, "status": response.reason, "body": response.content.decode()}


async def find_all_installations():
    "find all installations for the authenticated application"
    gh_app = await auth_app()
    jwt = gh_app["jwt"]
    uri = "https://api.github.com/app/installations"
    headers = util.set_headers(jwt, accept_headers["machine_man_preview"], True)
    response = requests.get(uri, params=None, headers=headers)
    # return the token and the response body
    # the token may be needed for additional authentication
    return {"jwt": jwt, "status": response.reason, "body": response.content.decode()}


async def get_single_installation(installation_id):
    "returns a particular installation for the application"
    gh_app = await auth_app()
    jwt = gh_app["jwt"]
    uri = f"https://api.github.com/app/installations/{installation_id}"
    headers = util.set_headers(jwt, accept_headers["machine_man_preview"], True)
    response = requests.get(uri, params=None, headers=headers)
    return {"jwt": jwt, "status": response.reason, "body": response.content.decode()}


async def find_org_installation(org, token):
    "find all installations of the app in the particular organization"
    uri = f"https://api.github.com/orgs{org}/installation"
    headers = util.set_headers(jwt, accept_headers["machine_man_preview"], True)
    response = requests.get(uri, params=None, headers=headers)
    return {"jwt": token, "status": response.reason, "body": response.content.decode()}


async def auth_installation(installation_id):
    "authenticate as a GitHub Installation to access more advanced API"
    # for an application to authenticate as a GitHub Installation, it first must authenticate as a GitHub App
    gh_installation = await get_single_installation(installation_id)
    jwt = gh_installation["jwt"]
    app_body = json.loads(gh_installation["body"])
    uri = app_body["access_tokens_url"]
    headers = util.set_headers(jwt, accept_headers["machine_man_preview"], True)
    response = requests.post(uri, data=None, headers=headers)
    # status is Created if the app was authorized successfully
    # return the installation token that can be used to access more advanced endpoints
    return {"status": response.reason, "body": response.content.decode()}
