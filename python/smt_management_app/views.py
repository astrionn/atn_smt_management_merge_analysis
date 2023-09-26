import json
import csv
from pprint import pprint as pp

import operator
from functools import reduce

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, generics

from django.http import JsonResponse
from django.core.files import File

from . serializers import *

from . models import AbstractBaseModel, Manufacturer, Provider, Article, Carrier, Machine, MachineSlot, Storage, StorageSlot, Job, Board, BoardArticle, LocalFile
# created by todo.org tangle
# Create your views here.

def store_carrier_confirm(request,carrier,slot):
   queryset = Carrier.objects.filter(name=carrier)
   if not queryset: return
   queryset2 = StorageSlot.objects.filter(name=slot)
   if not queryset2: return
   c = queryset.first()
   ss = queryset2.first()
   if ss.led_state == 0: return 
   c.storage_slot = ss
   c.save()
   ss.led_state = 1
   #thread to ledstate 0 in 15s

def store_carrier(request,carrier,storage):
   #is carrier storable ?
   #print(carrier,storage)
   carriers = Carrier.objects.filter(name=carrier)
   #print(carriers)
   if not carriers: return
   c = carriers.first()
   #print(c.__dict__)
   if c.collecting: return
   if c.archived: return
   if not c.delivered: return
   if c.storage_slot: return
   if c.machine_slot: return


   #free storage slot for storage ?
   storages = Storage.objects.filter(name=storage)
   #print(storages)
   if not storages: return
   storage = storages.first()
   #print(storage)
   free_slots = StorageSlot.objects.filter(carrier__isnull=True,storage=storage)
   #print(free_slots)
   fs = free_slots.first()
   fs.led_state = 2
   fs.save()
   msg = {
      'storage':storage.name,
      'slot':fs.name,
      "carrier":c.name
      }
   return JsonResponse(msg)


def collect_carrier(request,carrier):
   c = Carrier.objects.filter(name=carrier).first()

   #get queue and add
   queryset = Carrier.objects.filter(collecting=True)
   if c in queryset: return
   c.collecting = True
   c.save()
   queryset = Carrier.objects.filter(collecting=True)
   queue = [{
      'carrier':cc.name,
      'storage':cc.storage_slot.storage.name,
      'slot':cc.storage_slot.name
   } for cc in queryset]

   msg = {
      'storage':c.storage_slot.storage.name,
      'slot':c.storage_slot.name,
      'carrier':c.name,
      'queue':queue
          }
   c.storage_slot.led_state = 2
   return JsonResponse(msg)

def collect_carrier_confirm(request,carrier,slot):
   #get queue
   queryset = Carrier.objects.filter(collecting=True)
   #check membership
   queryset = queryset.filter(name=carrier)

   if not queryset: return
   c = queryset.first()

   #check slot correct
   if c.storage_slot.name != slot: return
   c.storage_slot.led_state = 1
   c.save()
   #thread led state off in 15s

   #set slot to null
   c.storage_slot = None
   #remove vom queue
   c.collecting = False
   c.save()
   #return storage, slot, carrier queue
   queryset = Carrier.objects.filter(collecting=True)
   queue = [{
      'carrier':cc.name,
      'storage':cc.storage_slot.storage.name,
      'slot':cc.storage_slot.name
   } for cc in queryset]

   msg = {
      'storage':None,
      'slot':None,
      'carrier':c.name,
      'queue':queue
          }
   return JsonResponse(msg)

class ListStoragesAPI(generics.ListAPIView):
    model = Carrier
    serializer_class = CarrierSerializer
    def get_queryset(self):
        storage = self.kwargs['storage']
        s = Storage.objects.get(name=storage)
        slots_qs = StorageSlot.objects.filter(storage=s)
        queryset = Carrier.objects.filter(storage_slot__in=slots_qs)
        return queryset

def user_mapping_and_file_processing(request):
  if request.POST:
    file_name = request.POST['file_name']
    map_ = request.POST['map']
    map_ = json.loads(map_)
    map_l = [(k,v) for k,v in map_.items()]


    lf = LocalFile.objects.get(name=file_name)
    msg = {'created':[],'fail':[]}
    with open(lf.file_object.name) as f:
      csv_reader = csv.reader(f,delimiter=',')
      a_headers = csv_reader.__next__()
      index_map = {value: index for index, value in enumerate(a_headers)}
      map_ordered_l = sorted(map_l,key=lambda x:index_map[x[1]])

      for l in csv_reader:
                #print(l)
        if lf.upload_type == 'board':
           if not request.POST['board'] or not Board.objects.filter(name=request.POST['board']):
              msg['fail'].append(f"Board does not exist.")
              break
           board = Board.objects.get(name=request.POST['board'])

           board_article_dict = {k[0]:l[a_headers.index(k[1])] for k in map_ordered_l}
           board_article_dict['board'] = board
           a = Article.objects.filter(name=board_article_dict['article'])
           if a :
               board_article_dict['article'] = a[0]
           else:
               msg['fail'].append(f"{board_article_dict['article']} does not exist.")
               print(msg)
               break
           if not board_article_dict.get('count',None) or not board_article_dict['count'].isnumeric():
              msg['fail'].append(f"{board_article_dict['article']} does have invalid count.")
              break
           board_article_dict['name'] = f"{board.name}_{board_article_dict['article'].name}"
           b_article = BoardArticle.objects.create(**board_article_dict)
           msg['created'].append(f"{board_article_dict['name']}")
                  
               

        if lf.upload_type == 'carrier':
           carrier_dict = {k[0]:l[a_headers.index(k[1])] for k in map_ordered_l}
           #pp(carrier_dict)
           if carrier_dict.get('article',None):
              a = Article.objects.get(name=carrier_dict['article'])
              carrier_dict['article'] = a
           if not carrier_dict.get('storage_slot',None):
              carrier_dict['storage_slot'] = None
           if not carrier_dict.get('machine_slot',None):
              carrier_dict['machine_slot'] = None
           if not carrier_dict.get('boardarticle',None):
              carrier_dict['boardarticle'] = None


           c = Carrier.objects.create(**carrier_dict)
           msg['created'].append(c.name)

        if lf.upload_type == 'article':
          article_dict = {k[0]:l[a_headers.index(k[1])] for k in map_ordered_l}

          if article_dict['manufacturer']:
            o_m,c_m = Manufacturer.objects.get_or_create(name=article_dict['manufacturer'])
            if c_m: 
              article_dict['manufacturer'] = o_m
              msg['created'].append(o_m.name)

            if article_dict['provider']:
              pps = article_dict['provider'].split(',')
              del article_dict['provider']
              providers = []
              for p in pps:
                o_p,c_p = Provider.objects.get_or_create(name=p)
                if c_p:
                  providers.append(o_p)
                  msg['created'].append(o_p.name)
            if article_dict['boardarticle']:
              del article_dict['boardarticle']

            c = Article.objects.create(**article_dict)
            if c : msg['created'].append(c.name)
            for p in providers:
              c.provider.add(p)
            c.save()

      msg_j = json.dumps(msg)
      return JsonResponse(msg_j,safe=False)

def save_file_and_get_headers(request):
    if request.FILES and request.POST:
        lf = LocalFile.objects.create(file_object=File(request.FILES["file"]), upload_type=request.POST["upload_type"])
        #open file
        with open(lf.file_object.path,newline='') as f:
            csv_reader = csv.reader(f,delimiter=',')
            lf.headers = list(csv_reader.__next__())
            lf.save()
        if lf.upload_type == 'article':
            model_fields = [f.name for f in Article._meta.get_fields()]
        elif lf.upload_type == 'carrier':
            model_fields = [f.name for f in Carrier._meta.get_fields()]
        elif lf.upload_type == 'board':
            model_fields = ['article','count']

        return JsonResponse({
            "object_fields":sorted(model_fields),
            "header_fields":sorted(lf.headers),
            "file_name":lf.name
        })

class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    filter_backends = (filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter)
    ordering_fields = [
      "name",
      "provider__name",
      "manufacturer__name",
      "sap_number",
      "created_at",
      "updated_at",
      "archived"
  ]

    search_fields = [
     "name",
     "description",
     "provider__name",
     "provider_description",
     "manufacturer__name",
     "manufacturer_description"
     "sap_number",
     "created_at",
     "updated_at",
     "archived"
  ]

    def get_queryset(self):
       name = self.request.GET.get('name') 
       description = self.request.GET.get('description')

       manufacturers_list = self.request.GET.getlist("manufacturers[]")
       providers_list = self.request.GET.getlist("providers[]")

       filter_args = {
          "name__icontains":name,
          "description__icontains":description,
          "archived" : False,
          }
       # print(filter_args)       

       filter_args = dict((k,v) for k,v in filter_args.items() if (v is not None and v != "" and v != []) )

       articles = Article.objects.filter(**filter_args)
       if len(manufacturers_list) > 0:
          articles = articles.filter(reduce(operator.or_, (Q(manufacturer__name__icontains=x) for x in manufacturers_list)))

       return articles

class BoardViewSet(viewsets.ModelViewSet):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer

class BoardArticleViewSet(viewsets.ModelViewSet):
    queryset = BoardArticle.objects.all()
    serializer_class = BoardArticleSerializer

class CarrierViewSet(viewsets.ModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer
    filter_backends = (filters.SearchFilter, DjangoFilterBackend, filters.OrderingFilter)
    ordering_fields = [
     "name",
     "lot_number",
     "quantity_current",
     "article__name",
     "delivered",
     "reserved",
  ]
    search_fields = [
     "name",
     "lot_number",
     "article__name",
     "article__description",
     "storage_slot__storage__name"
  ]

    def get_queryset(self):
       name = self.request.GET.get('name')
       lot_number = self.request.GET.get('lot_number')
       filter_args = {
        "name__icontains":name,
        "lot_number__icontains":lot_number,
     }
       filter_args = dict((k,v) for k,v in filter_args.items() if (v is not None and v != "" and v != []) )
       carriers = Carrier.objects.filter(**filter_args)
       return carriers

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer

class MachineViewSet(viewsets.ModelViewSet):
    queryset = Machine.objects.all()
    serializer_class = MachineSerializer

class MachineSlotViewSet(viewsets.ModelViewSet):
    queryset = MachineSlot.objects.all()
    serializer_class = MachineSlotSerializer

class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer

class ProviderViewSet(viewsets.ModelViewSet):
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer

class StorageViewSet(viewsets.ModelViewSet):
    queryset = Storage.objects.all()
    serializer_class = StorageSerializer

class StorageSlotViewSet(viewsets.ModelViewSet):
    queryset = StorageSlot.objects.all()
    serializer_class = StorageSlotSerializer
