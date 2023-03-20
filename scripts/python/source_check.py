"""Update python."""
import sys
import requests

from version import Version

URL = "https://www.python.org/downloads"

curr_ver = (sys.version).split()
current = Version(curr_ver[0])

request = requests.get(URL, timeout=120).text
upstream = Version(request.split(">Download Python ")[2].split("<")[0])

if current != upstream:
    print(upstream)
