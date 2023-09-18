from pprint import pprint as pp
import requests
import csv

client = requests.session()

path = "C:\\Users\\LB\\Downloads\\file.csv"
url = "http://localhost:8000/api/"
files = {"file":open(path,'rb'),"upload_type":"article"}

r = client.get("http://localhost:8000/login/")
if 'csrftoken' in client.cookies:
    csrftoken = client.cookies['csrftoken']
    print(csrftoken)

r1 = client.post(f"{url}save_file_and_get_headers/",files,cookies={'csrftoken':csrftoken})
pp(r1.__dict__)
pp(r1.json())


        
