import json
import csv
from pprint import pprint as pp

import io
import qrcode
from PIL import Image

from functools import reduce

from django_filters.rest_framework import DjangoFilterBackend

from django.middleware.csrf import get_token
from django.views.decorators.csrf import requires_csrf_token, csrf_exempt


from django_filters import rest_framework as rest_filter
import django_filters
from rest_framework import viewsets, filters, generics

from django.http import FileResponse, JsonResponse
from django.core.files import File


from .serializers import *

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


from .utils.neolight_handler import NeoLightAPI

# from .utils.PTL_handler import PTL_API
# from .utils.xgate_handler import NeoWrapperXGate

# from .utils.dymoHandler import DymoHandler

from threading import Thread

try:
    # initalize 3rd party handlers for connected devices like smart shelfs and label printers

    class NeoDummy:
        # for developement without actually having to connect a shelf
        def __init__(self):
            pass

        def led_on(self, lamp, color):
            print(f"led on {lamp=} ; {color=}")

        def led_off(self, lamp):
            print(f"led of {lamp=}")

        def reset_leds(self, working_light=False):
            print("reset leds")

    neo = NeoDummy()

    # neo = NeoLightAPI("192.168.178.11")  # weytronik
    # neo = PTL_API("COM16") # ATN inhouse
    # neo = NeoWrapperXGate("192.168.0.10")

    class DymoDummy:
        # for developement without actually having to connect a printer
        def print_label(self, text1, text2):
            print(f"printing label {text1,text2}")

    dymo = DymoDummy()
    # dymo = DymoHandler()

except Exception as e:
    print(666, e)


@csrf_exempt
def print_carrier(request, carrier):
    """
    Print a label for the given carrier containing barcode information.

    Args:
    - request: HTTP request object
    - carrier: Name of the carrier to print the label for

    Returns:
    - JsonResponse: Success or failure message
    """

    # Check if the carrier exists
    try:
        carrier_obj = Carrier.objects.get(name=carrier)
    except Carrier.DoesNotExist:
        return JsonResponse({"success": False, "message": "Carrier not found"})

    article = carrier_obj.article

    if not dymo:  # Assuming dymo is defined somewhere
        return JsonResponse(
            {"success": False, "message": "Dymo label printer not reachable"}
        )

    # Start a thread to print the label
    Thread(
        target=dymo.print_label, args=(carrier_obj.name, article.name), daemon=True
    ).start()

    return JsonResponse({"success": True})


@csrf_exempt
def test_leds(request):
    # only used for messe demonstrations, usually hidden from the frontend
    Thread(
        target=neo.test_higher_layer(),
    ).start()
    return JsonResponse({"test_led": True})


def dashboard_data(request):
    """
    Fetches data for the dashboard including total carriers, undelivered carriers,
    carriers in storage, available storage slots, and active storages.
    """
    total_carriers = Carrier.objects.filter(archived=False).count()
    undelivered_carriers = Carrier.objects.filter(
        archived=False, delivered=False
    ).count()
    carriers_in_storage = Carrier.objects.filter(
        archived=False, storage_slot__isnull=False
    ).count()
    free_slots = StorageSlot.objects.filter(carrier__isnull=True).count()
    active_storages = Storage.objects.filter(archived=False).count()

    return JsonResponse(
        {
            "total_carriers": total_carriers,
            "not_delivered": undelivered_carriers,
            "in_storage": carriers_in_storage,
            "free_slots": free_slots,
            "storages": active_storages,
        }
    )


def collect_carrier_by_article(request, storage, article):
    """
    Collects a carrier by article from a storage unit.
    Lights up slots containing the specified article.

    Args:
    - request: HTTP request object
    - storage: Storage object where the article is stored
    - article: Article number to collect

    Returns:
    - JsonResponse indicating success or failure
    """
    slots = StorageSlot.objects.filter(carrier__article__name=article, storage=storage)

    if not slots.exists():
        return JsonResponse(
            {
                "success": False,
                "message": f"Could not find a slot with article {article} in storage {storage}",
            }
        )

    # Activate LEDs for slots containing the article
    for slot in slots:
        Thread(target=neo.led_on, kwargs={"lamp": slot.name, "color": "green"}).start()

    return JsonResponse({"success": True})


def confirm_carrier_by_article(request, storage, article, carrier):
    """
    Confirms carrier by article from a storage unit.
    Empties the slot and resets LEDs upon carrier confirmation.

    Args:
    - request: HTTP request object
    - storage: Storage object where the carrier is located
    - article: Article number of the carrier
    - carrier: Carrier name to confirm

    Returns:
    - JsonResponse indicating success or failure
    """
    slot = StorageSlot.objects.filter(
        carrier__article__name=article, storage=storage, carrier__name=carrier
    )

    if not slot.exists():
        return JsonResponse(
            {
                "success": False,
                "message": f"Could not find a slot in storage {storage} that contains carrier {carrier} with article {article}",
            }
        )

    c = Carrier.objects.get(name=carrier)
    c.storage_slot = None
    c.storage = None
    c.save()

    # Reset LEDs after carrier confirmation
    Thread(target=neo.reset_leds).start()

    return JsonResponse({"success": True})


@csrf_exempt
def reset_leds(request, storage):
    """
    Resets LEDs and updates the LED state of storage slots.

    Args:
    - request: HTTP request object.
    - storage: Storage information.

    Returns:
    - JsonResponse: JSON response indicating LED reset status.
    """
    # Start a new thread to reset LEDs with working_light set to True
    Thread(target=neo.reset_leds, kwargs={"working_light": True}).start()

    # Update LED state for all storage slots to 0
    StorageSlot.objects.all().update(led_state=0)

    # Return JSON response indicating LED reset for the given storage
    return JsonResponse({"reset_led": storage})


def check_unique(request, field, value):
    # for evaluating/indicating uniqueness while the user is typing in a field where unqiueness is required
    if field == "sapnumber":
        unique = not Article.objects.filter(sap_number=value).exists()
        return JsonResponse({"success": unique})


def check_pk_unique(request, model_name, value):
    # for evaluating/indicating uniqueness while the user is typing in a field where unqiueness is required ; pk abstraction
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
def store_carrier_choose_slot(request, carrier, storage):
    # the user asks to store a carrier in a storage, if that is possible all possible slots LEDs for the storage get turned on, we send back the storage and slots for the user to confirm collection in the next step
    carrier = carrier.strip()  # remove whitespace
    carriers = Carrier.objects.filter(name=carrier)
    if not carriers:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    c = carriers.first()
    if c.collecting:
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

    storages = Storage.objects.filter(name=storage)
    if not storages:
        return JsonResponse({"success": False, "message": "No storage found."})
    storage = storages.first()

    free_slots = StorageSlot.objects.filter(
        carrier__isnull=True, storage=storage
    )  # later on take carrier size into consideration here
    if len(free_slots) == 0:
        return JsonResponse(
            {
                "success": False,
                "message": f"No free storage slots found in {storage.name}.",
            }
        )
    msg = {"storage": storage.name, "carrier": c.name, "slot": [], "success": True}
    if not hasattr(neo, "_LED_On_Control"):
        for fs in free_slots:
            fs.led_state = 2
            fs.save()
            Thread(
                target=neo.led_on,
                kwargs={"lamp": fs.name, "color": "blue"},
            ).start()
            msg["slot"].append(fs.name)
    else:
        neo._LED_On_Control(
            {
                "lamps": {
                    neo.side_row_lamp_to_led_address(fs.name): "blue"
                    for fs in free_slots
                }
            }
        )

    return JsonResponse(msg)


@csrf_exempt
def store_carrier_choose_slot_confirm(request, carrier, slot):
    # see store carrier choose slot

    carrier = carrier.strip()  # remove whitespace
    slot = slot.strip()  # remove whitespace
    queryset = Carrier.objects.filter(name=carrier)
    if not queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})

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
    ss.save()
    Thread(
        target=neo.reset_leds,
    ).start()

    return JsonResponse(
        {
            "success": True,
            "message": f"Carrier {c.name} stored in storage {ss.storage.name} slot {ss.name}.",
        }
    )


@csrf_exempt
def store_carrier(request, carrier, storage):
    # the user asks to store a carrier in a storage, if that is possible a slot is chosen and the corresponding LED turned on, we send back the storage and slot for the user to confirm collection in the next step
    carrier = carrier.strip()  # remove whitespace
    carriers = Carrier.objects.filter(name=carrier)
    if not carriers:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    c = carriers.first()
    if c.collecting:
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

    storages = Storage.objects.filter(name=storage)
    if not storages:
        return JsonResponse({"success": False, "message": "No free storage slot."})
    storage = storages.first()

    free_slots = StorageSlot.objects.filter(
        carrier__isnull=True, storage=storage
    )  # later on take carrier size into consideration here
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
    # see store carrier

    carrier = carrier.strip()  # remove whitespace
    slot = slot.strip()  # remove whitespace
    queryset = Carrier.objects.filter(name=carrier)
    if not queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})

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
    Thread(
        target=neo.led_off,
        kwargs={
            "lamp": slot,
        },
    ).start()
    ss.save()
    return JsonResponse({"success": True})


def collect_carrier(request, carrier):
    # the user asks to collect a carrier, if possible its added to the collect "queue"(its actually a set but queue sounds better) so the user can collect batchwise not one by one
    # in the next step the user scans all the carriers to make sure he collected the correct ones
    carrier = carrier.strip()  # remove whitespace
    c = Carrier.objects.filter(name=carrier).first()

    queryset = Carrier.objects.filter(collecting=True)  # collect queue
    if c in queryset:
        return JsonResponse({"success": False, "message": "Already in queue."})
    c.collecting = True  # add to queue
    c.save()
    queryset = Carrier.objects.filter(collecting=True)
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
    # see collect carrier

    carrier = carrier.strip()  # remove whitespace
    slot = slot.strip()  # remove whitespace
    queryset = Carrier.objects.filter(collecting=True)  # collect queue
    queryset = queryset.filter(name=carrier)  # is carrier in the queue?

    if not queryset:
        return JsonResponse(
            {
                "success": False,
                "message": f"Carrier {carrier} is not in the collect queue.",
            }
        )
    c = queryset.first()

    if c.storage_slot.name != slot:
        return JsonResponse(
            {
                "success": False,
                "message": f"Carrier {carrier} is in slot {c.storage_slot.name} not in slot {slot}",
            }
        )
    c.storage_slot.led_state = 0
    c.save()
    Thread(
        target=neo.led_off,
        kwargs={"lamp": c.storage_slot.name},
    ).start()

    c.storage_slot = None
    c.collecting = False
    c.save()
    queryset = Carrier.objects.filter(collecting=True)
    queue = [
        {
            "carrier": cc.name,
            "storage": cc.storage_slot.storage.name,
            "slot": cc.storage_slot.name,
        }
        for cc in queryset
    ]

    msg = {
        "success": True,
        "storage": None,
        "slot": None,
        "carrier": c.name,
        "queue": queue,
    }
    return JsonResponse(msg)


@csrf_exempt
def save_file_and_get_headers(request):
    # first step of a 2 step workflow to create articles/carriers from a csv file
    # this step saves the file for future processing and returns the headers of said csv file
    if request.FILES and request.POST:
        lf = LocalFile.objects.create(
            file_object=File(request.FILES["file"]),
            upload_type=request.POST["upload_type"],
        )
        try:
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
        except Exception as e:
            print(e)
            return JsonResponse({"success": False})
    return JsonResponse({"success": False})


@csrf_exempt
def user_mapping_and_file_processing(request):
    # first of all i am sorry for this monster, feel free to refactor when bored
    # this function is the abstraction for the user uploading csv files to create model instances with them, but the csv headers names do not have to correspond with
    # the models field names, because the user creates a mapping from the csv header names to the models field names in the frontend

    if request.POST:
        file_name = request.POST["file_name"]
        lf = LocalFile.objects.get(name=file_name)

        map_ = request.POST["map"]
        map_ = json.loads(map_)
        map_l = [
            (k, v) for k, v in map_.items() if v
        ]  # remove fields that have empty values

        msg = {"created": [], "fail": []}

        with open(lf.file_object.name) as f:
            csv_reader = csv.reader(f, delimiter=",")

            a_headers = csv_reader.__next__()  # 1st row contains the column headers

            # the following comprehensions takes the text to text mapping from the user to a index based mapping i.e. nth csv header corresponds to the mth model field
            index_map = {value: index for index, value in enumerate(a_headers)}
            map_ordered_l = sorted(map_l, key=lambda x: index_map[x[1]])

            for l in csv_reader:
                if lf.upload_type == "board":
                    if not request.POST["board"] or not Board.objects.filter(
                        name=request.POST["board"]
                    ):
                        msg["fail"].append(
                            f"Board {request.POST['board']} does not exist."
                        )
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
                    if not carrier_dict.get("diameter", None):
                        carrier_dict["diameter"] = 7
                    if not carrier_dict.get("width", None):
                        carrier_dict["width"] = 8
                    if not carrier_dict.get("container_type", None):
                        carrier_dict["container_type"] = 0
                    elif carrier_dict.get("container_type").lower() == "reel":
                        carrier_dict["container_type"] = 0
                    elif carrier_dict.get("container_type").lower() == "tray":
                        carrier_dict["container_type"] = 1
                    elif carrier_dict.get("container_type").lower() == "bag":
                        carrier_dict["container_type"] = 2
                    elif carrier_dict.get("container_type").lower() == "single":
                        carrier_dict["container_type"] = 3

                    if not Carrier.objects.filter(name=carrier_dict["name"]).exists():
                        c = Carrier.objects.create(**carrier_dict)
                        msg["created"].append(c.name)
                    else:
                        msg["fail"].append(carrier_dict["name"])

                if lf.upload_type == "article":
                    article_dict = {
                        k[0]: l[a_headers.index(k[1])] for k in map_ordered_l
                    }

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
                        (
                            provider1_object,
                            provider1_created,
                        ) = Provider.objects.get_or_create(
                            name=article_dict["provider1"]
                        )
                        article_dict["provider1"] = provider1_object
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


def create_qr_code(request, code):
    img = qrcode.make(code)
    buffer = io.BytesIO()
    img.save(buffer)
    buffer.seek(0)
    return FileResponse(buffer, filename=f"{code}.png")


class ListStoragesAPI(generics.ListAPIView):
    """List Storages API"""

    model = Carrier
    serializer_class = CarrierSerializer

    def get_queryset(self):
        """Retrieve Carrier queryset based on storage slots"""
        storage = self.kwargs["storage"]
        slots_qs = StorageSlot.objects.filter(storage__name=storage)
        queryset = Carrier.objects.filter(storage_slot__in=slots_qs)
        return queryset


class ArticleNameViewSet(generics.ListAPIView):
    """Article Name ViewSet"""

    model = Article

    def get(self, request):
        """Get all articles and serialize their names"""
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
