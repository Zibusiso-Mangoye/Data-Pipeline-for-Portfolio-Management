import json
import requests
import logging
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Optional

from pathlib import Path

from kedro.config import ConfigLoader
from kedro.framework.project import settings

conf_path = str(Path("/workspaces/Data-Pipeline-for-Portfolio-Management/gold-analysis") / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path)
credentials = conf_loader["credentials"]

session = requests.Session()
def send_http_request(url: str, headers: Optional[dict] = None, params: Optional[dict] = None) -> requests.Response:
    """
    Perform an HTTP request with optional headers and parameters.

    Args:
        url (str): The URL to send the HTTP request to.
        headers (dict, optional): A dictionary of headers to include in the request.
        params (dict, optional): A dictionary of query parameters to include in the request.

    Returns:
        Response: A Response object representing the HTTP response.
    """
    try:
        response = session.get(url, headers=headers, params=params)
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP Request Error: {e}")
        custom_response = requests.models.Response()
        custom_response.url = url
        custom_response.error = str(e)
        custom_response.status_code = 400  

        return custom_response

def get_market_data(url: str, params: dict):
    
    params["apikey"] = credentials['twelvedata_api_key']
    
    response = send_http_request(url, params=params)
    content = response.text
    json_data = json.loads(content, strict=False)
    df = pd.DataFrame(json_data['values'])
    
    return df
    