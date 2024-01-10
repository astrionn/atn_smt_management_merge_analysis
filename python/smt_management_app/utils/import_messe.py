import requests
import csv
import sys
import random
from pprint import pprint as pp
import time

client = requests.session()

base_url = "localhost"

path = "C:\\Users\\LB\\Downloads\\SMD_Artikel.csv"
path2 = "C:\\Users\\LB\\Documents\\productronica_dempo_reels.txt"
url = f"http://{base_url}:8000/api/article/"
url2 = f"http://{base_url}:8000/api/carrier/"
url3 = f"http://{base_url}:8000/api/storageslot/"
url4 = f"http://{base_url}:8000/api/storage/?format=json"
url5 = f"http://{base_url}:8000/api/manufacturer/"


resp_storage = client.get(url4)
storage = resp_storage.json()
if not storage["results"]:
    resp_create_storage = client.post(url4, {"name": "storage1", "capacity": 1000})
    resp_create_storage2 = client.post(url4, {"name": "storage2", "capacity": 1000})
    pp(resp_create_storage.json())
    pp(resp_create_storage2.json())
    for i in (
        list(range(1001, 1051))
        + list(range(2002, 2051))
        + list(range(3002, 3051))
        + list(range(4002, 4051))
    ):
        data3 = {
            "name": i,
            "storage": "storage1",
        }
        data3b = {
            "name": i,
            "storage": "storage2",
        }
        print(i, data3)
        resp3 = client.post(url3, json=data3)

        print(i, data3b)
        resp3b = client.post(url3, json=data3)

with open(path, encoding="latin_1") as f:
    data = list(csv.reader(f, delimiter=","))

with open(path2, encoding="latin_1") as f:
    names = f.readlines()
print(names)
headers = data[0]

pp(list(enumerate(headers)))
for i, l in enumerate(data[1:]):
    if i == 100:
        break
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
    if names:
        name = names.pop()
    else:
        name = f"C{str(i+1).zfill(3)}"
    data2 = {
        "name": name,
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
