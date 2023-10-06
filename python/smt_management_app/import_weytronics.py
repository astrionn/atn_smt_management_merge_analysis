import requests
import csv
import sys
import random
from pprint import pprint as pp

client = requests.session()

path = "C:\\Users\\LB\\Downloads\\SMD_Artikel.csv"
url = "http://localhost:8000/api/article/"
url2 = "http://localhost:8000/api/carrier/"
with open(path,encoding="latin_1") as f:
    data = list(csv.reader(f,delimiter=','))
    
headers = data[0]

print(list(enumerate(headers)))
for l in data[1:]:
    data = {
    'name':(None,l[0]),
    'description':(None,l[2]),
    'manufacturer':(None,l[6]),
    'manufacturer_description':(None,l[7]),
    }
    resp = client.post(url,files=data)
    if len(sys.argv) < 2:
        continue

    data2 = {
        'name':f"carrier_{random.randint(1,1000000)}",
        'quantity_current':1000,
        'article':l[0]
    }
    
    resp2 = client.post(url2,files=data2)
    pp(resp2.__dict__)





        