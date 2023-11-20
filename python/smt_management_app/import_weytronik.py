import requests
import csv
import sys
import random
from pprint import pprint as pp
import time


def led_address_to_side_row_lamp(led_address):
    if led_address < 1 or led_address > 1400:
        raise ValueError("LED address should be between 1 and 1400.")

    side = "001" if led_address < 701 else "002"
    if led_address > 700:
        led_address -= 700
    row = (led_address - 1) // 100 + 1
    lamp = (led_address - 1) % 100 + 1

    return f"{str(side).zfill(3)}-{str(row).zfill(2)}-{str(lamp).zfill(3)}"


def side_row_lamp_to_led_address(input_string):
    side, row, lamp = input_string.split("-")
    if len(side) != 3 or len(row) != 2 or len(lamp) != 3:
        raise ValueError("Invalid input format.")

    side = int(side)
    row = int(row)
    lamp = int(lamp)

    if side not in [1, 2] or row < 1 or row > 14 or lamp < 1 or lamp > 100:
        raise ValueError("Invalid input values.")

    if side == 1:
        led_address = (row - 1) * 100 + lamp
    else:
        led_address = 700 + (row - 1) * 100 + lamp

    return led_address


client = requests.session()

base_url = "localhost"

path = "C:\\Users\\LB\\Downloads\\SMD_Artikel.csv"
url = f"http://{base_url}:8000/api/article/"
url2 = f"http://{base_url}:8000/api/carrier/"
url3 = f"http://{base_url}:8000/api/storageslot/"
url4 = f"http://{base_url}:8000/api/storage/?format=json"
url5 = f"http://{base_url}:8000/api/manufacturer/"
"""
resp_storage = client.get(url4)
storage = resp_storage.json()
if not storage["results"]:
    resp_create_storage = client.post(url4, {"name": "storage1", "capacity": 1000})
    pp(resp_create_storage.json())
    for i in range(1, 1401):
        data3 = {
            "name": led_address_to_side_row_lamp(i),
            "storage": "storage1",
        }
        print(i, data3)
        resp3 = client.post(url3, json=data3)
"""

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
