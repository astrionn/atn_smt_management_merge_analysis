import requests
import csv

client = requests.session()

path = "C:\\Users\\LB\\Downloads\\SMD_Artikel.csv"
url = "http://localhost:8000/api/article/"
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

    
        