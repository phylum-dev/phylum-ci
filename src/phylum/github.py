"""Provide methods for interacting with the GitHub API."""

from inspect import cleandoc
import os
import time
from typing import Any, Optional

import requests

from phylum.constants import PHYLUM_USER_AGENT, REQ_TIMEOUT
from phylum.logger import LOG, progress_spinner

# GitHub API version to use when making requests to the REST API.
# Reference: https://docs.github.com/rest/overview/api-versions
GITHUB_API_VERSION = "2022-11-28"

# These are the default headers that are included in all GitHub API requests
DEFAULT_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": GITHUB_API_VERSION,
    "User-Agent": PHYLUM_USER_AGENT,
}

# Reference URL for how to create a GitHub Personal Access Token (PAT)
PAT_REF = "https://docs.github.com/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token"


def get_headers(github_token: Optional[str] = None) -> dict[str, str]:
    """Get the headers to use for a GitHub API request.

    Authenticated requests are made by providing a GitHub token. The token can be passed by parameter
    or set with the `GITHUB_TOKEN` environment variable. Preference is given to the parameter.
    """
    # Start with the default headers
    headers = DEFAULT_HEADERS.copy()

    # Add an authorization header if a GitHub token is provided
    if github_token is None:
        # Even requests that do not require authorization can be made with authentication by providing the token as
        # an environment variable. This may be useful to bypass/extend the rate limit for unauthenticated requests.
        github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        # `Bearer` or `token` should work here, but `Bearer` appears to be more comprehensive, allowing for JWTs too.
        # Reference: https://docs.github.com/rest/overview/resources-in-the-rest-api#oauth2-token-sent-in-a-header
        headers["Authorization"] = f"Bearer {github_token}"

    return headers


@progress_spinner("Making GitHub API request")
def github_request(
    api_url: str,
    params: Optional[dict] = None,
    github_token: Optional[str] = None,
    timeout: float = REQ_TIMEOUT,
) -> Any:
    """Make a request to a given GitHub API endpoint and return the response.

    A limited amount of specific failure cases are checked to provide detailed information to users.
    All failure cases cause the system to exit with a failure code and a detailed message.

    Valid GitHub API requests will return a JSON-formatted response body, usually a dict or list.
    """
    headers = get_headers(github_token=github_token)

    LOG.debug("Making request to GitHub API URL: %s", api_url)
    resp = requests.get(api_url, headers=headers, params=params, timeout=timeout)

    # The returned headers of any GitHub API request can be viewed to see the current rate limit status.
    # Reference: https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limit-http-headers
    rate_limit_remaining = resp.headers.get("x-ratelimit-remaining", "unknown")
    rate_limit = resp.headers.get("x-ratelimit-limit", "unknown")
    rate_limit_reset_header = int(resp.headers.get("x-ratelimit-reset", "0"))
    current_time = time.asctime(time.localtime())
    if not rate_limit_reset_header:
        LOG.warning("`x-ratelimit-reset` header not available; using 1 hour from current time instead")
        seconds_in_hour = 60 * 60
        rate_limit_reset_header = int(time.mktime(time.localtime()) + seconds_in_hour)
    reset_time = time.asctime(time.localtime(rate_limit_reset_header))

    # There are several reasons why a 403 status code (FORBIDDEN) could be returned:
    #   * API rate limit exceeded
    #   * API secondary rate limit exceeded
    #   * Failed login limit exceeded
    #   * Requests with no `User-Agent` header
    # Reference: https://docs.github.com/rest/overview/resources-in-the-rest-api
    #
    # The most likely reason is that the rate limit has been exceeded so check for that.
    # The other possible forbidden cases are not common enough to check for here.
    # Reference: https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting
    if resp.status_code == requests.codes.forbidden and rate_limit_remaining == "0":
        msg = f"""
            GitHub API rate limit of {rate_limit} requests/hour was exceeded for
            URL: {api_url}
            The current time is:  {current_time}
            Rate limit resets at: {reset_time}
            Options include waiting to try again after the rate limit resets
            or to make authenticated requests by providing a GitHub token in
            the `GITHUB_TOKEN` environment variable. Reference:
            {PAT_REF}"""
        raise SystemExit(cleandoc(msg))

    LOG.debug("%s GitHub API requests remaining until window resets at: %s", rate_limit_remaining, reset_time)

    # Wrap all other request failures in a detailed message and exit with that instead of a stack trace
    try:
        resp.raise_for_status()
    except requests.HTTPError as err:
        msg = f"""
            A bad request was made to the GitHub API:
            {err}
            Response text: {resp.text.strip()}"""
        raise SystemExit(cleandoc(msg)) from err

    resp_json = resp.json()

    return resp_json
