import os
import requests as req

# api.weather.gov rejects requests without a User-Agent, so send one by
# default. NWS etiquette asks for a contact string; set COASTAL_CONTACT
# (see coastal.env) to your own. The fallback carries no personal info.
DEFAULT_USER_AGENT = os.environ.get(
    'COASTAL_CONTACT', 'brads-weather-report (https://github.com/)'
)


def get_json_request(
    api_url: str,
    params: dict = None,
    token: str = None,
    headers: dict = None
):
    """
    Makes an API request and returns the JSON response.

    Args:
        api_url (str): Link to web API.
        params (dict): Parameter fields with valid values.
        token (str): Bearer token for authorization.
        headers (dict): Extra request headers, merged over the
            defaults (e.g. an Accept override).

    Returns:
        response (dict): JSON formatted output, or None if the
        request failed.
    """
    request_headers = {"User-Agent": DEFAULT_USER_AGENT}
    if token is not None:
        request_headers["Authorization"] = f"Bearer {token}"
    if headers:
        request_headers.update(headers)
    try:
        response = req.get(api_url, params=params, headers=request_headers)
        response.raise_for_status()
    except req.exceptions.HTTPError as e:
        code = e.response.status_code
        reason = e.response.reason
        print(f"Request failed: {api_url}: {code} - {reason}")
        return None
    except req.exceptions.RequestException as e:
        print(f"Request failed (no response): {api_url}: {e}")
        return None
    data = response.json()
    return data


def save_grib_request(api_url: str, file_path: str, params: dict = None):
    try:
        response = req.get(
            api_url,
            params=params,
            stream=True
        )
        response.raise_for_status()
    except req.exceptions.HTTPError as e:
        code = e.response.status_code
        reason = e.response.reason
        print(f"Request failed: {e.response.url}: {code} - {reason}")
        return None
    except req.exceptions.RequestException as e:
        print(f"Request failed (no response): {api_url}: {e}")
        return None
    with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)