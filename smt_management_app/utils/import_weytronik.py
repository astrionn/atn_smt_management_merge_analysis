import requests
import csv
import sys
import random
from pprint import pprint as pp
import time

client = requests.session()

base_url = "localhost"
if len(sys.argv)>0:
    base_url = sys.argv[0]

path = "C:\\Users\\LB\\Downloads\\SMD_Artikel.csv"
url = f"http://{base_url}:8000/api/article/"
url2 = f"http://{base_url}:8000/api/carrier/"
url3 = f"http://{base_url}:8000/api/storageslot/"
url4 = f"http://{base_url}:8000/api/storage/?format=json"
url5 = f"http://{base_url}:8000/api/manufacturer/"

with open(path, encoding="latin_1") as f:
    data = list(csv.reader(f, delimiter=","))

headers = data[0]

pp(list(enumerate(headers)))
for i, l in enumerate(data[1:]):
    data = {
        "name": (None, l[0]),
        "description": (None, l[2]),
        "manufacturer": (None, l[6]),
        "manufacturer_description": (None, l[7]),
    }

    manu = client.get(f"{url5}?name={l[6]}")
    manu = manu.json()
    # pp(manu)
    if manu["count"] == 0:
        manu_create = client.post(url5, {"name": l[6]})
        # pp(manu_create.__dict__)
    resp = client.post(url, files=data)
    if len(sys.argv) < 2:
        continue

    data2 = {
        "name": f"C{str(i+1).zfill(3)}",
        "quantity_current": l[3],
        "article": l[0],
        "lot_number": (i + 1) % 10,
        "delivered": True,
    }
    # pp(data2)
    # time.sleep(0.1)
    resp2 = client.post(url2, json=data2)
    # pp(resp2.__dict__)
    # print(resp.status_code, "\n")
