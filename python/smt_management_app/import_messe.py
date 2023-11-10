import requests
import csv
import sys
import random
from pprint import pprint as pp
import time

client = requests.session()

base_url = "localhost"

path = "C:\\Users\\LB\\Downloads\\SMD_Artikel.csv"
url = f"http://{base_url}:8000/api/article/"
url2 = f"http://{base_url}:8000/api/carrier/"
url3 = f"http://{base_url}:8000/api/storageslot/"
url4 = f"http://{base_url}:8000/api/storage/?format=json"
url5 = f"http://{base_url}:8000/api/manufacturer/"



resp_storage = client.get(url4)
storage = resp_storage.json()
if not storage["results"]:
    resp_create_storage = client.post(url4, {"name": "storage1", "capacity": 1000})
    pp(resp_create_storage.json())
    for i in list(range(1001,1051)) + list(range(2002,2051)) + list(range(3002,3051)) + list(range(4002,4051)):
        data3 = {
            "name": i,
            "storage": "storage1",
        }
        print(i, data3)
        resp3 = client.post(url3, json=data3)