import json
import csv
from pprint import pprint as pp
import re


from django_filters.rest_framework import DjangoFilterBackend

from django.middleware.csrf import get_token
from django.views.decorators.csrf import requires_csrf_token, csrf_exempt


from django_filters import rest_framework as rest_filter
import django_filters
from .serializers import ArticleNameSerializer, ArticleSerializer, BoardArticleSerializer, BoardSerializer, CarrierNameSerializer, CarrierSerializer, JobSerializer, MachineSerializer, MachineSlotSerializer, ManufacturerNameSerializer, ManufacturerSerializer, ProviderNameSerializer, ProviderSerializer, StorageSerializer, StorageSlotSerializer
from rest_framework import viewsets, filters, generics

from django.http import JsonResponse
from django.core.files import File


# from .serializers import *

from .models import (
    Manufacturer,
    Provider,
    Article,
    Carrier,
    Machine,
    MachineSlot,
    Storage,
    StorageSlot,
    Job,
    Board,
    BoardArticle,
    LocalFile,
)


from .xgate_handler import XGateHandler
from .dymoHandler import DymoHandler

from threading import Thread

try:
    dymo = None
    dymo = DymoHandler()

    # neo = NeoLightAPI("192.168.178.11")
    # neo = PTL_API("COM16")
    class Neo:
        def __init__(self):
            self.xgate = XGateHandler("192.168.0.10")

        def slot_to_row_led(self, lamp):
            row_part, led_part = lamp.split("-")
            return int(re.sub("B", "1", re.sub("A", "", row_part))), int(led_part)

        def led_on(self, lamp, color):
            row, led = self.slot_to_row_led(lamp)
            print(f"led switch: slot = {lamp} ; {row=} ; {led=}")
            self.xgate.switch_lights(address=row, lamp=led, col=color, blink=False)

        def led_off(self, lamp):
            self.led_on(lamp, "off")

        def reset_leds(self, working_light=False):
            print("reset leds")
            self.xgate.clear_leds()

    neo = Neo()
except Exception as e:
    print(666, e)

# created by todo.org tangle
# Create your views here.


@csrf_exempt
def print_carrier(request, carrier):
    carrierF = Carrier.objects.filter(name=carrier)
    if len(carrierF) > 0:
        carrier = carrierF.first()
        article = carrier.article
        if not dymo:
            return JsonResponse({"success": False})
        Thread(
            target=dymo.print_label, args=(carrier.name, article.name), daemon=True
        ).start()
        # dymo.print_label(carrier.name, article.name)
        return JsonResponse({"success": True})
    return JsonResponse({"success": False})


@csrf_exempt
def test_leds(request):
    Thread(
        target=neo.test_higher_layer(),
    ).start()
    return JsonResponse({"test_led": True})


def dashboard_data(request):
    total = Carrier.objects.filter(archived=False).count()
    undelivered = Carrier.objects.filter(archived=False, delivered=False).count()
    stored = Carrier.objects.filter(archived=False, storage_slot__isnull=False).count()
    free_slots = StorageSlot.objects.filter(carrier__isnull=True).count()
    storages = Storage.objects.filter(archived=False).count()

    return JsonResponse(
        {
            "total_carriers": total,
            "not_delivered": undelivered,
            "in_storage": stored,
            "storages": storages,
            "free_slots": free_slots,
        }
    )


def collect_carrier_by_article(request, storage, article):
    slots = StorageSlot.objects.filter(carrier__article__name=article, storage=storage)
    print(slots)
    if len(slots) == 0:
        return JsonResponse({"success": False})
    for slot in slots:
        Thread(target=neo.led_on, kwargs={"lamp": slot.name, "color": "green"}).start()

    return JsonResponse({"success": True})


def confirm_carrier_by_article(request, storage, article, carrier):
    slot = StorageSlot.objects.filter(
        carrier__article__name=article, storage=storage, carrier__name=carrier
    )
    print(slot)
    if len(slot) == 0:
        return JsonResponse({"success": False})
    c = Carrier.objects.get(name=carrier)
    c.storage_slot = None
    c.storage = None
    c.save()
    Thread(target=neo.reset_leds).start()
    return JsonResponse({"success": True})


@csrf_exempt
def reset_leds(request, storage):
    Thread(target=neo.reset_leds, kwargs={"working_light": True}).start()
    StorageSlot.objects.all().update(led_state=0)
    return JsonResponse({"reset_led": storage})


def check_unique(request, field, value):
    if field == "sapnumber":
        unique = not Article.objects.filter(sap_number=value).exists()
        return JsonResponse({"success": unique})


def check_pk_unique(request, model_name, value):
    if model_name.lower() == "carrier":
        model = Carrier

    if model_name.lower() == "article":
        model = Article

    try:
        model.objects.get(pk=value)
        is_unique = False
        error_message = "The primary key value is not unique."
    except model.DoesNotExist:
        is_unique = True
        error_message = None

    return JsonResponse(
        {
            "success": is_unique,
            "error_message": error_message,
        }
    )


@requires_csrf_token
def get_csrf_token(request):
    csrf_token = get_token(request)
    response = JsonResponse({"csrf_token": csrf_token})
    response["X-CSRFToken"] = csrf_token
    return response


@csrf_exempt
def store_carrier(request, carrier, storage):
    # is carrier storable ?
    # print(carrier,storage)
    carrier = carrier.strip()
    carriers = Carrier.objects.filter(name=carrier)
    # print(carriers)
    if not carriers:
        print("carrier not found")
        return JsonResponse({"success": False, "message": "Carrier not found."})
    c = carriers.first()
    # print(c.__dict__)
    if c.collecting:
        print("carrier is collecting")
        return JsonResponse({"success": False, "message": "Carrier is collecting."})
    if c.archived:
        return JsonResponse({"success": False, "message": "Carrier has been archived."})
    if not c.delivered:
        return JsonResponse(
            {"success": False, "message": "Carrier has not been delivered."}
        )
    if c.storage_slot:
        return JsonResponse({"success": False, "message": "Carrier is stored already."})
    if c.machine_slot:
        return JsonResponse({"success": False})

    # free storage slot for storage ?
    storages = Storage.objects.filter(name=storage)
    # print(storages)
    if not storages:
        return JsonResponse({"success": False, "message": "No free storage slot."})
    storage = storages.first()

    free_slots = StorageSlot.objects.filter(carrier__isnull=True, storage=storage)
    # print(free_slots)
    fs = free_slots.first()
    fs.led_state = 2
    fs.save()
    Thread(
        target=neo.led_on,
        kwargs={"lamp": fs.name, "color": "blue"},
    ).start()

    msg = {"storage": storage.name, "slot": fs.name, "carrier": c.name, "success": True}
    return JsonResponse(msg)


@csrf_exempt
def store_carrier_confirm(request, carrier, slot):
    # pp(request.__dict__)
    # print(carrier)
    # print(slot)
    carrier = carrier.strip()
    slot = slot.strip()
    # next 2 lines only for sophia at siemens wien
    slot = slot[-5:]
    slot = f"{slot[:2]}-{slot[2:]}"
    queryset = Carrier.objects.filter(name=carrier)
    if not queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})

    # print(slot)
    queryset2 = StorageSlot.objects.filter(name=slot)
    if not queryset2:
        return JsonResponse({"success": False, "message": "no slot found"})
    c = queryset.first()
    ss = queryset2.first()
    if ss.led_state == 0:
        return JsonResponse({"success": False, "message": "led is off but shouldn't"})
    c.storage_slot = ss
    c.save()
    ss.led_state = 0
    # thread to ledstate 0 in 15s
    Thread(
        target=neo.led_off,
        kwargs={
            "lamp": slot,
        },
    ).start()
    ss.save()
    return JsonResponse({"success": True})


def collect_carrier(request, carrier):
    carrier = carrier.strip()
    c = Carrier.objects.filter(name=carrier).first()

    # get queue and add
    queryset = Carrier.objects.filter(collecting=True)
    # print(queryset)
    if c in queryset:
        return JsonResponse({"success": False, "message": "Already in queue."})
    c.collecting = True
    c.save()
    queryset = Carrier.objects.filter(collecting=True)
    # print(queryset)
    queue = [
        {
            "carrier": cc.name,
            "storage": cc.storage_slot.storage.name,
            "slot": cc.storage_slot.name,
        }
        for cc in queryset
    ]

    msg = {
        "storage": c.storage_slot.storage.name,
        "slot": c.storage_slot.name,
        "carrier": c.name,
        "queue": queue,
    }
    c.storage_slot.led_state = 2
    Thread(
        target=neo.led_on, kwargs={"lamp": c.storage_slot.name, "color": "green"}
    ).start()
    return JsonResponse(msg)


def collect_carrier_confirm(request, carrier, slot):
    carrier = carrier.strip()
    slot = slot.strip()
    # get queue
    queryset = Carrier.objects.filter(collecting=True)
    # check membership
    queryset = queryset.filter(name=carrier)

    if not queryset:
        return
    c = queryset.first()

    # check slot correct
    if c.storage_slot.name != slot:
        return
    c.storage_slot.led_state = 0
    c.save()
    Thread(
        target=neo.led_off,
        kwargs={"lamp": c.storage_slot.name},
    ).start()

    # set slot to null
    c.storage_slot = None
    # remove vom queue
    c.collecting = False
    c.save()
    # return storage, slot, carrier queue
    queryset = Carrier.objects.filter(collecting=True)
    queue = [
        {
            "carrier": cc.name,
            "storage": cc.storage_slot.storage.name,
            "slot": cc.storage_slot.name,
        }
        for cc in queryset
    ]

    msg = {"storage": None, "slot": None, "carrier": c.name, "queue": queue}
    return JsonResponse(msg)


class ListStoragesAPI(generics.ListAPIView):
    model = Carrier
    serializer_class = CarrierSerializer

    def get_queryset(self):
        storage = self.kwargs["storage"]
        s = Storage.objects.get(name=storage)
        slots_qs = StorageSlot.objects.filter(storage=s)
        queryset = Carrier.objects.filter(storage_slot__in=slots_qs)
        return queryset


@csrf_exempt
def user_mapping_and_file_processing(request):
    if request.POST:
        file_name = request.POST["file_name"]
        map_ = request.POST["map"]
        map_ = json.loads(map_)
        map_l = [(k, v) for k, v in map_.items() if v]
        lf = LocalFile.objects.get(name=file_name)
        msg = {"created": [], "fail": []}
        with open(lf.file_object.name) as f:
            csv_reader = csv.reader(f, delimiter=",")
            a_headers = csv_reader.__next__()
            index_map = {value: index for index, value in enumerate(a_headers)}
            map_ordered_l = sorted(map_l, key=lambda x: index_map[x[1]])
            for l in csv_reader:
                if lf.upload_type == "board":
                    if not request.POST["board"] or not Board.objects.filter(
                        name=request.POST["board"]
                    ):
                        msg["fail"].append(f"Board does not exist.")
                        break
                    board = Board.objects.get(name=request.POST["board"])

                    board_article_dict = {
                        k[0]: l[a_headers.index(k[1])] for k in map_ordered_l
                    }
                    board_article_dict["board"] = board
                    a = Article.objects.filter(name=board_article_dict["article"])
                    if a:
                        board_article_dict["article"] = a[0]
                    else:
                        msg["fail"].append(
                            f"{board_article_dict['article']} does not exist."
                        )
                        # print(msg)
                        break
                    if (
                        not board_article_dict.get("count", None)
                        or not board_article_dict["count"].isnumeric()
                    ):
                        msg["fail"].append(
                            f"{board_article_dict['article']} does have invalid count."
                        )
                        break
                    board_article_dict[
                        "name"
                    ] = f"{board.name}_{board_article_dict['article'].name}"
                    b_article = BoardArticle.objects.create(**board_article_dict)
                    msg["created"].append(f"{board_article_dict['name']}")

                if lf.upload_type == "carrier":
                    carrier_dict = {
                        k[0]: l[a_headers.index(k[1])] for k in map_ordered_l
                    }

                    if carrier_dict.get("article", None):
                        a = Article.objects.get(name=carrier_dict["article"])
                        carrier_dict["article"] = a
                    if not carrier_dict.get("storage_slot", None):
                        carrier_dict["storage_slot"] = None
                    if not carrier_dict.get("machine_slot", None):
                        carrier_dict["machine_slot"] = None
                    if not carrier_dict.get("boardarticle", None):
                        carrier_dict["boardarticle"] = None
                    if not Carrier.objects.filter(name=carrier_dict["name"]).exists():
                        c = Carrier.objects.create(**carrier_dict)
                        msg["created"].append(c.name)
                    else:
                        msg["fail"].append(carrier_dict["name"])

                if lf.upload_type == "article":
                    article_dict = {
                        k[0]: l[a_headers.index(k[1])] for k in map_ordered_l
                    }
                    print(0, article_dict)

                    if (
                        "manufacturer" in article_dict.keys()
                        and article_dict["manufacturer"]
                    ):
                        o_m, c_m = Manufacturer.objects.get_or_create(
                            name=article_dict["manufacturer"]
                        )
                        article_dict["manufacturer"] = o_m
                        if c_m:
                            msg["created"].append(o_m.name)

                    if "provider1" in article_dict.keys() and article_dict["provider1"]:
                        print(f'creating provider1 :{article_dict["provider1"]}')
                        (
                            provider1_object,
                            provider1_created,
                        ) = Provider.objects.get_or_create(
                            name=article_dict["provider1"]
                        )
                        article_dict["provider1"] = provider1_object
                        print(provider1_object)
                        if provider1_created:
                            msg["created"].append(provider1_object.name)
                    if "provider2" in article_dict.keys() and article_dict["provider2"]:
                        (
                            provider2_object,
                            provider2_created,
                        ) = Provider.objects.get_or_create(
                            name=article_dict["provider2"]
                        )
                        article_dict["provider2"] = provider2_object
                        if provider2_created:
                            msg["created"].append(provider2_object.name)
                    if "provider3" in article_dict.keys() and article_dict["provider3"]:
                        (
                            provider3_object,
                            provider3_created,
                        ) = Provider.objects.get_or_create(
                            name=article_dict["provider3"]
                        )
                        article_dict["provider3"] = provider3_object
                        if provider3_created:
                            msg["created"].append(provider3_object.name)
                    if "provider4" in article_dict.keys() and article_dict["provider4"]:
                        (
                            provider4_object,
                            provider4_created,
                        ) = Provider.objects.get_or_create(
                            name=article_dict["provider4"]
                        )
                        article_dict["provider4"] = provider4_object
                        if provider4_created:
                            msg["created"].append(provider4_object.name)
                    if "provider5" in article_dict.keys() and article_dict["provider5"]:
                        (
                            provider5_object,
                            provider5_created,
                        ) = Provider.objects.get_or_create(
                            name=article_dict["provider5"]
                        )
                        article_dict["provider5"] = provider5_object
                        if provider5_created:
                            msg["created"].append(provider5_object.name)

                    if (
                        "boardarticle" in article_dict.keys()
                        and article_dict["boardarticle"]
                    ):
                        del article_dict["boardarticle"]
                    if not Article.objects.filter(name=article_dict["name"]).exists():
                        pp(article_dict)
                        o_a = Article.objects.create(
                            **{k: v for k, v in article_dict.items() if k and v}
                        )
                        c_a = True
                    else:
                        c_a = False

                    if c_a:
                        msg["created"].append(o_a.name)
                    else:
                        msg["fail"].append(article_dict["name"])

        msg_j = json.dumps(msg)
        return JsonResponse(msg, safe=False)
    return JsonResponse({"success": "false"})


@csrf_exempt
def save_file_and_get_headers(request):
    # print(request.FILES)
    # print(request.POST)

    if request.FILES and request.POST:
        lf = LocalFile.objects.create(
            file_object=File(request.FILES["file"]),
            upload_type=request.POST["upload_type"],
        )
        # open file
        with open(lf.file_object.path, newline="") as f:
            csv_reader = csv.reader(f, delimiter=",")
            lf.headers = list(csv_reader.__next__())
            lf.save()
            if lf.upload_type == "article":
                model_fields = [f.name for f in Article._meta.get_fields()]
            elif lf.upload_type == "carrier":
                model_fields = [f.name for f in Carrier._meta.get_fields()]
            elif lf.upload_type == "board":
                model_fields = ["article", "count"]
            return JsonResponse(
                {
                    "object_fields": sorted(model_fields),
                    "header_fields": sorted(lf.headers),
                    "file_name": lf.name,
                }
            )
    return JsonResponse({"success": False})


class ArticleNameViewSet(generics.ListAPIView):
    model = Article

    def get(self, request):
        queryset = Article.objects.all()
        serializer = ArticleNameSerializer(queryset, many=True)
        data = [{k: v for k, v in a.items()} for a in serializer.data]
        return JsonResponse(data, safe=False)


class ArticleFilter(rest_filter.FilterSet):
    provider1__name = rest_filter.CharFilter(method="provider_filter")
    provider2__name = rest_filter.CharFilter(method="provider_filter")
    provider3__name = rest_filter.CharFilter(method="provider_filter")
    provider4__name = rest_filter.CharFilter(method="provider_filter")
    provider5__name = rest_filter.CharFilter(method="provider_filter")

    class Meta:
        model = Article
        fields = {
            "name": ["exact", "contains"],
            "description": ["exact", "contains"],
            "manufacturer__name": ["exact", "contains"],
            "manufacturer_description": ["exact", "contains"],
            "provider1__name": ["exact", "contains"],
            "provider1_description": ["exact", "contains"],
            "provider2__name": ["exact", "contains"],
            "provider2_description": ["exact", "contains"],
            "provider3__name": ["exact", "contains"],
            "provider3_description": ["exact", "contains"],
            "provider4__name": ["exact", "contains"],
            "provider4_description": ["exact", "contains"],
            "provider5__name": ["exact", "contains"],
            "provider5_description": ["exact", "contains"],
            "sap_number": ["exact", "contains"],
            "created_at": ["exact", "contains", "gte", "lte"],
            "updated_at": ["exact", "contains", "gte", "lte"],
            "archived": ["exact"],
        }

    def provider_filter(self, queryset, name, value):
        qs = queryset.filter(
            models.Q(provider1__name__contains=value)
            | models.Q(provider2__name__contains=value)
            | models.Q(provider3__name__contains=value)
            | models.Q(provider4__name__contains=value)
            | models.Q(provider5__name__contains=value)
        )
        return qs


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    filter_backends = (
        rest_filter.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_class = ArticleFilter
    ordering_fields = "__all__"


class BoardViewSet(viewsets.ModelViewSet):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer


class BoardArticleViewSet(viewsets.ModelViewSet):
    queryset = BoardArticle.objects.all()
    serializer_class = BoardArticleSerializer


class CarrierNameViewSet(generics.ListAPIView):
    model = Carrier

    def get(self, request):
        queryset = Carrier.objects.all()
        serializer = CarrierNameSerializer(queryset, many=True)
        data = [{k: v for k, v in c.items()} for c in serializer.data]
        return JsonResponse(data, safe=False)


class CarrierFilter(django_filters.FilterSet):
    # There is no default filtering system for selection fields,
    # I implemented a custom option for gt and lt, if you don’t need them, you can simply delete them
    article__provider1__name = rest_filter.CharFilter(method="article_provider_filter")
    article__provider2__name = rest_filter.CharFilter(method="article_provider_filter")
    article__provider3__name = rest_filter.CharFilter(method="article_provider_filter")
    article__provider4__name = rest_filter.CharFilter(method="article_provider_filter")
    article__provider5__name = rest_filter.CharFilter(method="article_provider_filter")

    class Meta:
        model = Carrier
        fields = {
            "name": ["exact", "contains"],
            "diameter": ["exact", "gt", "lt"],
            "width": ["exact", "gt", "lt"],
            "container_type": ["exact", "gt", "lt"],
            "quantity_original": ["exact", "gt", "lt"],
            "quantity_current": ["exact", "gt", "lt"],
            "lot_number": ["exact", "contains"],
            "reserved": ["exact"],
            "delivered": ["exact"],
            "collecting": ["exact"],
            "article__name": ["exact", "contains"],
            "article__description": ["exact", "contains"],
            "article__manufacturer__name": ["exact", "contains"],
            "article__manufacturer_description": ["exact", "contains"],
            "article__provider1__name": ["exact", "contains"],
            "article__provider2__name": ["exact", "contains"],
            "article__provider3__name": ["exact", "contains"],
            "article__provider4__name": ["exact", "contains"],
            "article__provider5__name": ["exact", "contains"],
            "article__sap_number": ["exact", "contains"],
            "storage_slot__name": ["exact", "contains"],
            "storage__name": ["exact", "contains"],
            "machine_slot__name": ["exact", "contains"],
            "archived": ["exact"],
            "created_at": ["exact", "contains", "gte", "lte"],
            "updated_at": ["exact", "contains", "gte", "lte"],
        }

    def article_provider_filter(self, queryset, name, value):
        qs = queryset.filter(
            models.Q(article__provider1__name__contains=value)
            | models.Q(article__provider2__name__contains=value)
            | models.Q(article__provider3__name__contains=value)
            | models.Q(article__provider4__name__contains=value)
            | models.Q(article__provider5__name__contains=value)
        )
        return qs


class CarrierViewSet(viewsets.ModelViewSet):
    queryset = Carrier.objects.all()
    serializer_class = CarrierSerializer
    filter_backends = (
        filters.SearchFilter,
        DjangoFilterBackend,
        filters.OrderingFilter,
    )
    filterset_class = CarrierFilter
    ordering_fields = [field.name for field in Carrier._meta.get_fields()] + [
        "article__manufacturer__name",
        "article__manufacturer_description",
        "article__description",
        "article__sap_number",
    ]
    search_fields = "__all__"

    def get_queryset(self):
        name = self.request.GET.get("name")
        lot_number = self.request.GET.get("lot_number")
        storage = self.request.GET.get("storage")
        filter_args = {
            "name__icontains": name,
            "lot_number__icontains": lot_number,
            "storage__name__icontains": storage,
        }
        filter_args = dict(
            (k, v)
            for k, v in filter_args.items()
            if (v is not None and v != "" and v != [])
        )
        carriers = Carrier.objects.filter(**filter_args)
        return carriers


class JobFilter(django_filters.FilterSet):
    class Meta:
        model = Job
        fields = {
            "name": ["exact", "contains"],
            "board__name": ["exact", "icontains"],
            "machine__name": ["exact", "icontains"],
            "project": ["exact", "icontains"],
            "customer": ["exact", "icontains"],
            "count": ["exact", "gt", "lt"],
            "start_at": ["exact", "gte", "lte"],
            "finish_at": ["exact", "gte", "lte"],
            "status": ["exact"],
            "archived": ["exact"],
            "created_at": ["exact", "contains", "gte", "lte"],
            "updated_at": ["exact", "contains", "gte", "lte"],
        }


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    filterset_class = JobFilter


class MachineViewSet(viewsets.ModelViewSet):
    queryset = Machine.objects.all()
    serializer_class = MachineSerializer


class MachineSlotViewSet(viewsets.ModelViewSet):
    queryset = MachineSlot.objects.all()
    serializer_class = MachineSlotSerializer


class ManufacturerFilter(rest_filter.FilterSet):
    class Meta:
        model = Manufacturer
        fields = {
            "name": ["exact", "contains"],
        }


class ManufacturerNameViewSet(generics.ListAPIView):
    model = Manufacturer

    def get(self, request):
        queryset = Manufacturer.objects.all()
        serializer = ManufacturerNameSerializer(queryset, many=True)
        data = [{k: v for k, v in c.items()} for c in serializer.data]
        return JsonResponse(data, safe=False)


class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    filterset_class = ManufacturerFilter
    filter_backends = (
        filters.SearchFilter,
        DjangoFilterBackend,
        filters.OrderingFilter,
    )

    ordering_fields = "__all__"
    search_fields = "__all__"


class ProviderNameViewSet(generics.ListAPIView):
    model = Provider

    def get(self, request):
        queryset = Provider.objects.all()
        serializer = ProviderNameSerializer(queryset, many=True)
        data = [{k: v for k, v in c.items()} for c in serializer.data]
        return JsonResponse(data, safe=False)


class ProviderViewSet(viewsets.ModelViewSet):
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer


class StorageViewSet(viewsets.ModelViewSet):
    queryset = Storage.objects.all()
    serializer_class = StorageSerializer


class StorageSlotViewSet(viewsets.ModelViewSet):
    queryset = StorageSlot.objects.all()
    serializer_class = StorageSlotSerializer
