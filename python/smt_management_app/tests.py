from pprint import pprint as pp
import os 
import json
import datetime
import pytz
from logging import getLogger, DEBUG
from random import randint
import random


from django.test import TestCase
from django.test.client import Client
from django.utils.timezone import get_default_timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile

from . models import AbstractBaseModel, Manufacturer, Provider, Article, Carrier, Machine, MachineSlot, Storage, StorageSlot, Job, Board, BoardArticle

# Create your tests here.
# created by todo.org tangle

UserModel = get_user_model()

class CommonSetUpTestCase(TestCase):

  user_model = None,
  CLIENT = None,
  TZ = None,
  USER_EMAIL = None,
  PASSWORD = None,
  USERNAME = None,
  logger = None

  @classmethod
  def setUp(cls) -> None:

    cls.logger = getLogger(__name__)
    cls.logger.setLevel(level=DEBUG)
    cls.USERNAME = 'testuser'
    cls.PASSWORD = 'NeverUseThisPassword12345'
    cls.USER_EMAIL = 'test@storageguide.com'
    cls.TZ = get_default_timezone()
    cls.CLIENT = Client(enforce_csrf_checks=False)

    try:
      cls.user_model = UserModel.objects.get(username=cls.USERNAME)
    except ObjectDoesNotExist:
      cls.user_model = UserModel.objects.create_user(
        username=cls.USERNAME,
        password=cls.PASSWORD,
        email=cls.USER_EMAIL,
      )




    printing = False  
    #verfiy setup worked and display all fields and method in the class dict of the testcase
    if printing:
      from pprint import pprint as pp
      print("\n\n",cls,"\n\n",cls.__dict__,"\n\n")
      for name,att in cls.__dict__.items():
        print(name,att)
        print(f"\n\nMy Name is \"{name}\" !\nMy class is \"{att.__class__}\" It's name is \"{att.name if isinstance(att,AbstractBaseModel) else att}\"\n")
        if isinstance(att,AbstractBaseModel):
          pp(att.__dict__)
          pass

  @classmethod
  def print_qs(cls,qs):
    #print the dict of every object return in the queryset
    if not qs: return
    for o in qs:
      print(o,o.__dict__,'\n')
      pass

  @classmethod
  def get_random_name(cls,prefix=None):
    return f"{prefix}_{randint(1,1000)}"

  @classmethod
  def login_client(cls):
    cls.logger.info('Logging in client...')
    cls.CLIENT.login(
      username=cls.USERNAME,
      password=cls.PASSWORD
    )

  @classmethod
  def logout_client(cls):
    cls.logger.info("Logging out client...")
    cls.CLIENT.logout()


  def test_view_creating_article(cls):
    rand_name = cls.get_random_name("article")
    resp_create = cls.CLIENT.post("/api/article/",{
      "name":rand_name,
      "description":"123123123123123"
    })
    jdata = resp_create.json()
    resp_display = cls.CLIENT.get(f"/api/article/{rand_name}/?format=json")

    jdata2 = resp_display.json()
    #pp(jdata)
    #pp(jdata2)
    cls.assertEqual(jdata,jdata2)
    return jdata2

  def test_view_creating_carrier(cls):
    art_json = cls.test_view_creating_article()
    #print(art_json)
    rand_name = cls.get_random_name("carrier")
    data = {
                                    "name":rand_name,
                                    "article":art_json['name'],
                                    "quantity_current":1000
                                  }
    #pp(data)
    resp_create = cls.CLIENT.post("/api/carrier/", data)
    

    jdata = resp_create.json()
    #pp(jdata)
    resp_display = cls.CLIENT.get(f"/api/carrier/{rand_name}/?format=json")

    jdata2 = resp_display.json()
    #pp(jdata)
    #pp(jdata2)
    cls.assertEqual(jdata,jdata2)
    return jdata2

  def test_view_creating_articles_from_file(cls):
    """tests a 2-step workflow:
        - uploading a csv file and getting the userspace headers and getting the file name returned
        - sending a mapping from user space to internal space of headers along with the filename and getting success or failure message of creation 
    """

    #all fields and relations of Article model
    headers = ["name","provider","provider_description","manufacturer","manufacturer_description","description","sap_number","created_at","updated_at","archived",'board','boardarticle','carrier']

    #add some random to it to simulate the user having different names to our internal representation
    headers_salted = [k+cls.get_random_name("_aaaa") for k in headers]

    #build csv file
    file_content = ",".join(headers_salted)
    file_content += '\n'

    for i in range(5):
      values = []
      for h in headers:
        if h == 'provider':
          values.append(f"\"{cls.get_random_name(h)},{cls.get_random_name(h)}\"")
        elif h in ["archived"]:
          values.append(str(True))
        else:
          values.append(cls.get_random_name(h))

      file_content += ",".join(values)
      file_content += '\n'


    f = SimpleUploadedFile("file.csv",bytes(file_content,encoding="utf8"), content_type='text/plain')

    #upload csv file 
    resp_create = cls.CLIENT.post("/api/save_file_and_get_headers/",{'file':f,'upload_type':'article'})
    resp_create_json = resp_create.json()

    headers_salted2 = resp_create_json["header_fields"]
    headers2 = resp_create_json["object_fields"]
    file_name = resp_create_json["file_name"]

    cls.assertEqual(sorted(headers_salted),sorted(headers_salted2))
    cls.assertEqual(sorted(headers),sorted(headers2))

    #provide user mapping
    map_ = {k:v for k,v in zip(sorted(headers),sorted(headers_salted2))}
    #post
    resp_map = cls.CLIENT.post("/api/user_mapping_and_file_processing/",{'file_name':file_name,'map':json.dumps(map_)})
    msg = resp_map.json()


  def test_view_creating_carriers_from_file(cls):
    """tests a 2-step workflow:
        - uploading a csv file and getting the userspace headers and getting the file name returned
        - sending a mapping from user space to internal space of headers along with the filename and getting success or failure message of creation 
    """

    #all fields and relations of Carrier model (Carrier._meta.fields)
    headers = [
      'name',
      'created_at',
      'updated_at',
      'archived', 
      'article',
      'boardarticle',
      'diameter', 
      'width', 
      'container_type', 
      'quantity_original', 
      'quantity_current', 
      'lot_number', 
      'reserved', 
      'delivered', 
      'collecting', 
      'storage_slot', 
      'machine_slot'
      ]

    #add some random to it to simulate the user having different names to our internal representation
    headers_salted = [k+cls.get_random_name("_aaaa") for k in headers]

    #build csv file
    file_content = ",".join(headers_salted)
    file_content += '\n'

    for i in range(5):
      values = []
      for h in headers:
        if h in ["archived","collecting","reserved"]:
          values.append(str(False))
        elif h in ["delivered"]:
          values.append(str(True))
        elif h in ["created_at","updated_at","storage_slot","machine_slot",'boardarticle']:
          values.append('')
        elif h in ['article']:
          art_randname = cls.get_random_name('article')
          a = Article.objects.create(name=art_randname)
          values.append(a.name)
        elif h in ["diameter"]:
          values.append(7)
        elif h in ["width"]:
          values.append(8)
        elif h in ["container_type"]:
          values.append(0)
        elif h in ["quantity_current","quantity_original"]:
          values.append(1000)
        elif h in ['name']:
          values.append(cls.get_random_name("carrier"))
        else:
          values.append(cls.get_random_name(h))
      values = [str(v) for v in values]
      file_content += ",".join(values)
      file_content += '\n'


    f = SimpleUploadedFile("file.csv",bytes(file_content,encoding="utf8"), content_type='text/plain')

    #upload csv file 
    resp_create = cls.CLIENT.post("/api/save_file_and_get_headers/",{'file':f,'upload_type':'carrier'})
    resp_create_json = resp_create.json()

    headers_salted2 = resp_create_json["header_fields"]
    headers2 = resp_create_json["object_fields"]
    file_name = resp_create_json["file_name"]
    
    cls.assertEqual(sorted(headers_salted),sorted(headers_salted2))
    cls.assertEqual(sorted(headers),sorted(headers2))

    #provide user mapping
    map_ = {k:v for k,v in zip(sorted(headers),sorted(headers_salted2))}
    #post
    resp_map = cls.CLIENT.post("/api/user_mapping_and_file_processing/",{'file_name':file_name,'map':json.dumps(map_)})
    msg = resp_map.json()
    #pp(msg)
    
  #create a csv file with bunch of articles
  #get_csv_headers(file) -> file_name
  #create_articles_from_file(file_name,headers) -> created X didnt create Y
  #Articles.objects.all
  #assert equal

  def test_view_displaying_carriers(cls):
    #create carriers with different attributes 
    data = {
      "articles":[cls.get_random_name("article") for _ in range(3)],
      "manufacturers":[cls.get_random_name("manufacturer") for _ in range(3)],
      "providers":[cls.get_random_name("provider") for _ in range(3)],
      "lot_numbers":[cls.get_random_name("lot_number") for _ in range(3)]
      }
    
    for a in data["articles"]:
      cls.CLIENT.post("/api/article/",{"name":a})

    for m in data["manufacturers"]:  
      cls.CLIENT.post("/api/manufacturer/",{"name":m})

    for p in data["providers"]:
      cls.CLIENT.post("/api/provider/",{"name":p})


    carriers = [{
      "name":cls.get_random_name("carrier"),
      "article":random.choice(data["articles"]) ,
      "manufacturer":random.choice(data["manufacturers"]),
      "provider":random.choice(data["providers"]),
      "lot_number":random.choice(data["lot_numbers"]),
      "quantity_current":1000
    } for i in range(3)]
    carriers_clean = [{k:v for k,v in c.items() if k not in ['provider','manufacturer']} for c in carriers]
    resps = []
    for c in carriers:
      resp = cls.CLIENT.post("/api/carrier/",c)
      resps.append(resp.json())
    
    #get carriers 

    resp = cls.CLIENT.get("/api/carrier/?format=json")
    jdata = resp.json()
    jdata_clean = [{k:v for k,v in j.items() if k in carriers[0].keys()} for j in jdata]
    
    #pp(carriers_clean)
    #pp(jdata)
    #pp(jdata_clean)
    cls.assertEqual(jdata_clean,carriers_clean)

  def test_view_deleting_carriers(cls):
    art_randname = cls.get_random_name("article")
    a = Article.objects.create(name=art_randname)
    
    car_randname = cls.get_random_name("carrier")
    c = Carrier.objects.create(name=car_randname,article=a,quantity_current=1000)
    
    c_qs = Carrier.objects.filter(name=car_randname).first()
    cls.assertEqual(c,c_qs)
    
    resp_del = cls.CLIENT.delete(f"/api/carrier/{c.name}/")
    
    cls.assertEqual(Carrier.objects.filter(name=car_randname).first(),None)
    
    

  def test_view_delivering_carriers(cls):
    #Article.objects.create
    #Carrier.objects.create
    #edit_carrier()
    #Carrier.objects.all
    #assertEqual
    #assert fail for old data
    art_randname = cls.get_random_name("article")
    a = Article.objects.create(name=art_randname)
    
    car_randname = cls.get_random_name("carrier")
    c = Carrier.objects.create(name=car_randname,article=a,quantity_current=1000)
    
    c_qs = Carrier.objects.filter(name=car_randname).first()
    #pp(c_qs.__dict__)
    cls.assertEqual(c,c_qs)

    resp_edit = cls.CLIENT.patch(f"/api/carrier/{car_randname}/",{"quantity_current":999})
    c_qs_1 = Carrier.objects.filter(name=car_randname).first()
    #pp(c_qs_1.__dict__)

  def test_view_QR_printing_carriers(cls):
    pass
  #Article.objects.create
  #Carrier.objects.create
  #print_label()

  def test_view_displaying_storages(cls):
    
  #Article.objects.create
  #Carrier.objects.create
  #Storage.objects.create
  #StorageSlot.objects.create
  #get_carriers(storage)

    art_randname = cls.get_random_name("article")
    a = Article.objects.create(name=art_randname)
    
    car_randname = cls.get_random_name("carrier")
    c = Carrier.objects.create(name=car_randname,article=a,quantity_current=1000)

    car_randname2 = cls.get_random_name("carrier")
    c2 = Carrier.objects.create(name=car_randname2,article=a,quantity_current=1000)
    
    stor_randname = cls.get_random_name("storage")
    s = Storage.objects.create(name=stor_randname,capacity=1000)

    stor_slot_randname = cls.get_random_name("storage_slot")
    ss = StorageSlot.objects.create(name=stor_slot_randname,storage=s)

    stor_slot_randname2 = cls.get_random_name("storage_slot")
    ss2 = StorageSlot.objects.create(name=stor_slot_randname2,storage=s)

    c.storage_slot = ss
    c.save()
    c2.storage_slot = ss2
    c2.save()
    resp_display = cls.CLIENT.get(f"/api/get_storage_content/{s.name}/?format=json")
    #pp(resp_display.json())
    #pp([c.__dict__,c2.__dict__])


  def test_view_collect_carriers(cls):
    art_randname = cls.get_random_name("article")
    a = Article.objects.create(name=art_randname)
    
    car_randname = cls.get_random_name("carrier")
    c = Carrier.objects.create(name=car_randname,article=a,quantity_current=1000)

    car_randname2 = cls.get_random_name("carrier")
    c2 = Carrier.objects.create(name=car_randname2,article=a,quantity_current=1000)
    
    stor_randname = cls.get_random_name("storage")
    s = Storage.objects.create(name=stor_randname,capacity=1000)

    stor_slot_randname = cls.get_random_name("storage_slot")
    ss = StorageSlot.objects.create(name=stor_slot_randname,storage=s)

    stor_slot_randname2 = cls.get_random_name("storage_slot")
    ss2 = StorageSlot.objects.create(name=stor_slot_randname2,storage=s)

    c.storage_slot = ss
    c.save()
    c2.storage_slot = ss2
    c2.save()

    #collect_carrier(carrier) -> storage, slot, carrier, queue
    resp_collect = cls.CLIENT.get(f'/api/collect_carrier/{car_randname}/')
    resp_collect2 = cls.CLIENT.get(f'/api/collect_carrier/{car_randname2}/')
    #pp(resp_collect.__dict__)
    #pp(resp_collect2.__dict__)
    jdata = resp_collect.json()
    jdata2 = resp_collect2.json()
    
    #pp(jdata2)
    slot = jdata['slot']
    slot2 = jdata2['slot']
    #collect carrier_confirm_slot(slot, carrier) -> storage, slot, carrier, queue
    resp_confirm = cls.CLIENT.post(f'/api/collect_carrier_confirm/{car_randname}/{slot}/')
    #pp(resp_confirm.json())
    resp_confirm2 = cls.CLIENT.post(f'/api/collect_carrier_confirm/{car_randname2}/{slot2}/')
    #pp(resp_confirm2.json())

  def test_view_collect_carriers_job(cls):
    pass
  #Article.objects.create
  #Carrier.objects.create
  #Storage.objects.create
  #StorageSlot.objects.create
  #Board.objects.create
  #Job.objects.create
  #collect_carriers_job(job) -> queue
  #collect_carrier_confirm_slot(slot, carrier) -> storage, slot, carrier, queue



  def test_view_storing_carrier(cls):
    art_randname = cls.get_random_name("article")
    a = Article.objects.create(name=art_randname)
    
    car_randname = cls.get_random_name("carrier")
    c = Carrier.objects.create(name=car_randname,article=a,quantity_current=1000)
    c.delivered = True
    c.save()

    car_randname2 = cls.get_random_name("carrier")
    c2 = Carrier.objects.create(name=car_randname2,article=a,quantity_current=1000)
    c2.delivered = True
    c2.save()
    

    car_randname3 = cls.get_random_name("carrier")
    c3 = Carrier.objects.create(name=car_randname3,article=a,quantity_current=1000)
    c3.delivered = True
    c3.save()

    stor_randname = cls.get_random_name("storage")
    s = Storage.objects.create(name=stor_randname,capacity=1000)

    stor_slot_randname = cls.get_random_name("storage_slot")
    ss = StorageSlot.objects.create(name=stor_slot_randname,storage=s)

    stor_slot_randname2 = cls.get_random_name("storage_slot")
    ss2 = StorageSlot.objects.create(name=stor_slot_randname2,storage=s)

    stor_slot_randname3 = cls.get_random_name("storage_slot")
    ss3 = StorageSlot.objects.create(name=stor_slot_randname3,storage=s)
    c3.storage_slot = ss3
    c3.save()
    resp_store = cls.CLIENT.post(f"/api/store_carrier/{c.name}/{s.name}/")
    #pp(resp_store.__dict__)
    

  def test_view_resetting_leds(cls):
    pass
  #Storage.objects.create
  #StorageSlot.objects.create
  #reset_leds_for_storage(storage)


  def test_view_creating_job(cls):
    art_randname = cls.get_random_name("article")
    a = Article.objects.create(name=art_randname)

    art_randname2 = cls.get_random_name("article")
    a2 = Article.objects.create(name=art_randname2)
    
    car_randname = cls.get_random_name("carrier")
    c = Carrier.objects.create(name=car_randname,article=a,quantity_current=1000)

    car_randname2 = cls.get_random_name("carrier")
    c2 = Carrier.objects.create(name=car_randname2,article=a,quantity_current=1000)
    
    stor_randname = cls.get_random_name("storage")
    s = Storage.objects.create(name=stor_randname,capacity=1000)

    stor_slot_randname = cls.get_random_name("storage_slot")
    ss = StorageSlot.objects.create(name=stor_slot_randname,storage=s)

    stor_slot_randname2 = cls.get_random_name("storage_slot")
    ss2 = StorageSlot.objects.create(name=stor_slot_randname2,storage=s)

    c.storage_slot = ss
    c.save()
    c2.storage_slot = ss2
    c2.save()

    bor_randname = cls.get_random_name("board")
    resp_board_create = cls.CLIENT.post('/api/board/',{
      "name":bor_randname,
    })

    for ba in [art_randname,art_randname2]:
      resp_boardarticles_create = cls.CLIENT.post('/api/boardarticle/',{'name':f"{bor_randname}_{ba}","article":ba,'count':10,'board':bor_randname})
      #pp(resp_boardarticles_create.__dict__)
    
    bb = Board.objects.all()
    b = bb.first()
    #print(b)
    #print(b.boardarticle_set.all())
    #print(b.articles.all())
    job = {
      'name':cls.get_random_name('job'),
      'board':b.name,
      'count':100,
      'start_at':'2023-01-01 8:00:00.000',#iso-8601
      'finish_at':'2023-01-01 18:00:00.000'
    }
    resp_job_create = cls.CLIENT.post('/api/job/',job)
    #pp(resp_job_create.__dict__)

    resp_job_display = cls.CLIENT.get(f'/api/job/{job["name"]}/?format=json')
    #pp(resp_job_display.__dict__)

  def test_view_creating_board_from_file(cls):
    pass    
  #Article.objects.create
  #Carrier.objects.create
  #Storage.objects.create
  #StorageSlot.objects.create
  #Board.objects.create
  #Job.objects.create

  #create a csv file with bunch of article names and counts
  #get_csv_headers(file) -> file_name
  #create_board_from_file(file_name,headers) -> created X didnt create Y
  #Jobs.objects.get(name) -> Job
  #Job.board.articles
  #assert equal
