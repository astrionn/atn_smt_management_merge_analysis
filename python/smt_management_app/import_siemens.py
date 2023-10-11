import requests
import csv
import sys
import random
from pprint import pprint as pp
import time

client = requests.session()

path = "C:\\Users\\LB\\Downloads\\store.csv"
url = "http://localhost:8000/api/article/"
url2 = "http://localhost:8000/api/carrier/"
url3 = "http://localhost:8000/api/storageslot/"
url4 = "http://localhost:8000/api/storage/?format=json"
url5 = "http://localhost:8000/api/manufacturer/"


resp_storage = client.get(url4)
storage = resp_storage.json()
if not storage["results"]:
    resp_create_storage = client.post(url4, {"name": "storage1", "capacity": 1000})
    pp(resp_create_storage.json())
    for i in [303, 305, 307, 308, 309]:
        data3 = {"name": f"{str(i).zfill(3)}", "storage": "storage1"}
        resp3 = client.post(url3, json=data3)


with open(path, encoding="latin_1") as f:
    data = list(csv.reader(f, delimiter=","))

headers = data[0]

print(list(enumerate(headers)))
for i, l in enumerate(data[1:]):
    print("\n", l)
    data = {
        "name": (None, l[1]),
        "description": (None, l[2]),
        "manufacturer": (None, l[7]),
        "manufacturer_description": (None, l[8]),
    }

    manu = client.get(f"{url5}?name={l[7]}")
    manu = manu.json()
    # pp(manu)
    if manu["count"] == 0:
        manu_create = client.post(url5, {"name": l[7]})
        # pp(manu_create.__dict__)

    resp = client.post(url, files=data)
    pp(data)
    pp(resp.__dict__)
    pp(resp.request.__dict__)
    if len(sys.argv) < 2:
        continue

    data2 = {
        "name": l[0],
        "quantity_current": l[3],
        "article": l[1],
        "lot_number": l[9],
        "delivered": True,
    }
    # pp(data)
    # pp(data2)
    # time.sleep(0.1)
    resp2 = client.post(url2, json=data2)
    # pp(resp2.__dict__)
    # print(resp.status_code, "\n")
    continue
    if data2["name"] not in ["C030", "C029", "C031", "C036", "C049"]:
        resp_store = client.post(
            f"http://localhost:8000/api/store_carrier/{data2['name']}/storage1/"
        )
        jj = resp_store.json()
        # pp(jj)
        carrier = jj["carrier"]
        slot = jj["slot"]
        if slot in ["400", "401", "402", "403", "404", "405"]:
            continue
        time.sleep(0.1)
        resp_store_confirm = client.post(
            f"http://localhost:8000/api/store_carrier_confirm/{carrier}/{slot}/"
        )
        time.sleep(0.1)
