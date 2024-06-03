import os
import random
import string
from urllib.parse import urljoin

import giteapy
from giteapy.rest import ApiException

import requests
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route


GITEA_URL = os.environ.get("GITEA_URL", "")
CLIENT_ID = os.environ.get("CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "")
APP_URL = os.environ.get("APP_URL")
access_token = ""
if not all([GITEA_URL, CLIENT_ID, CLIENT_SECRET, APP_URL]):
    raise Exception("Please provide the GITEAURL, CLIENT_ID, and CLIENT_SECRET")


def random_string(length=10):
    return "".join(
        random.choice(string.ascii_lowercase + string.digits) for _ in range(length)
    )


state = random_string()
redirect_uri = urljoin(APP_URL, "/callback")
uri = f"/login/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&state={state}"


def login(request):
    return RedirectResponse(url=urljoin(GITEA_URL, uri))


def callback(request):
    returned_code = request.query_params.get("code")
    returned_state = request.query_params.get("state")

    if not returned_code:
        return JSONResponse("Unauthorized", 401)

    if returned_state != state:
        raise Exception("Invalid state")
    res = requests.post(
        urljoin(GITEA_URL, "/login/oauth/access_token"),
        json={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": returned_code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
    )

    token = res.json()
    global access_token
    access_token = token["access_token"]
    return RedirectResponse("/")


def get_repos(request):
    if not access_token:
        return RedirectResponse("/login")

    configuration = giteapy.Configuration()
    configuration.host = urljoin(GITEA_URL, "/api/v1")
    configuration.api_key["token"] = access_token
    # create an instance of the API class
    api_client = giteapy.ApiClient(configuration)
    api_instance = giteapy.UserApi(api_client)
    try:
        # Create an organization
        api_response = api_instance.user_current_list_repos()
        print(api_response)
        repos = []
        for repo in api_response:
            repos.append(repo.full_name)
    except ApiException as e:
        raise Exception("Exception when calling list organization repos: %s\n" % e)

    return JSONResponse(repos)


app = Starlette(
    debug=True,
    routes=[
        Route("/login", login),
        Route("/callback", callback),
        Route("/", get_repos),
    ],
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
