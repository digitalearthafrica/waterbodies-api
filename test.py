import requests

url = "http://localhost:8080/waterbody/53329/observations/csv"

with requests.get(url, stream=True) as r:
    for chunk in r.iter_content(512):  # or, for line in r.iter_lines():
        print(chunk)
