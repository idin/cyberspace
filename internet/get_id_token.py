import requests
import re
from requests_ntlm import HttpNtlmAuth
from getpass import getpass
import warnings


def get_id_token(url, username, password=None, num_tries=10):
    if password is None:
        credentials = HttpNtlmAuth(username=username, password=getpass())
    else:
        credentials = HttpNtlmAuth(username=username, password=password)
    session = requests.Session()
    token = None
    for i in range(num_tries):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = session.get(url, auth=credentials, verify=False, allow_redirects=False)
        url = response.headers['Location']
        try:
            token = re.search(r'id_token=(.+?)&', url).group(1)
            break
        except AttributeError:
            continue
    return token
