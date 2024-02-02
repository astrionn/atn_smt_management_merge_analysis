import json
import csv
import io
import qrcode
from threading import Thread


from django_filters.rest_framework import DjangoFilterBackend
from django.middleware.csrf import get_token
from django.views.decorators.csrf import requires_csrf_token, csrf_exempt
from django_filters import rest_framework as rest_filter
import django_filters
from django.http import FileResponse, JsonResponse
from django.core.files import File
from rest_framework import viewsets, filters, generics

from .serializers import (
    ArticleNameSerializer, ArticleSerializer, BoardArticleSerializer, BoardSerializer,
    CarrierNameSerializer, CarrierSerializer, JobSerializer, MachineSerializer,
    MachineSlotSerializer, ManufacturerNameSerializer, ManufacturerSerializer,
    ProviderNameSerializer, ProviderSerializer, StorageSerializer, StorageSlotSerializer
)
from .models import (
    Manufacturer, Provider, Article, Carrier, Machine, MachineSlot,
    Storage, StorageSlot, Job, Board, BoardArticle, LocalFile,
)
from smt_management_app import models


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


def assign_carrier_to_job(request, job, carrier):
    job_object = Job.objects.filter(name=job).first()
    carrier_object = Carrier.objects.filter(name=carrier,archived=False).first()

    if job_object and carrier_object:
        job_object.carriers.add(carrier_object)
        job_object.save()
        return JsonResponse({"success": True})
    else:
        return JsonResponse({"success": False})


def deliver_all_carriers(request):
    i = Carrier.objects.filter(archived=False).update(delivered=True)
    return JsonResponse({"success": True, "updated_amount": i})


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
        carrier_obj = Carrier.objects.get(name=carrier,archived=False)
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
    # only used for messe demonstrations, hidden from the frontend
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
    undelivered_carriers = Carrier.objects.filter(archived=False, delivered=False).count()
    carriers_in_storage = Carrier.objects.filter(archived=False, storage_slot__isnull=False).count()
    carriers_in_production = Carrier.objects.filter(archived=False, storage_slot__isnull=True, delivered=True).count()
    free_slots = StorageSlot.objects.filter(carrier__isnull=True).count()
    active_storages = Storage.objects.filter(archived=False).count()
    total_finished_jobs = Job.objects.filter(status=2).count()
    open_jobs_created = Job.objects.filter(archived=False,status=0).count()
    open_jobs_finished = Job.objects.filter(archived=False,status=2).count()

    return JsonResponse(
        {
            "total_carriers": total_carriers,
            "not_delivered": undelivered_carriers,
            "in_storage": carriers_in_storage,
            "in_production":carriers_in_production,
            "free_slots": free_slots,
            "storages": active_storages,
            "total_finished_jobs":total_finished_jobs,
            "open_jobs_created":open_jobs_created,
            "open_jobs_prepared":open_jobs_created,
            "open_jobs_finished":open_jobs_finished
        }
    )


def collect_carrier_by_article(request, article):
    """
    Collects a carrier by article from a storage unit.
    Lights up slots containing the specified article.

    Args:
    - request: HTTP request object
    - article: Article number to collect

    Returns:
    - JsonResponse indicating success or failure
    """
    article = article.strip()
    slots = StorageSlot.objects.filter(carrier__article__name=article,carrier_archived=False)

    if not slots.exists():
        return JsonResponse(
            {
                "success": False,
                "message": f"Could not find a carrier with article {article} in any storage",
            }
        )

    # Activate LEDs for slots containing the article
    for slot in slots:
        Thread(target=neo.led_on, kwargs={"lamp": slot.name, "color": "green"}).start()

    return JsonResponse({"success": True})

def confirm_carrier_by_article(request, article, carrier):
    """
    Confirms carrier by article from a storage unit.
    Empties the slot and resets LEDs upon carrier confirmation.

    Args:
    - request: HTTP request object
    
    - article: Article number of the carrier
    - carrier: Carrier name to confirm

    Returns:
    - JsonResponse indicating success or failure
    """
    article,carrier = article.strip(),carrier.strip()
    slot = StorageSlot.objects.filter(
        carrier__article__name=article, carrier__name=carrier
    )

    if not slot.exists():
        return JsonResponse(
            {
                "success": False,
                "message": f"Could not find a slot in that contains carrier {carrier} with article {article}",
            }
        )

    c = Carrier.objects.get(name=carrier,archived=False)
    c.storage_slot = None
    c.storage = None
    c.save()

    # Reset LEDs after carrier confirmation
    Thread(target=neo.reset_leds).start()
    # Update LED state for all storage slots to 0
    StorageSlot.objects.all().update(led_state=0)

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

    if model_name.lower() == "job":
        model = Job
    
    if model_name.lower() == "board":
        model = Board
    


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
    carrier = carrier.strip()
    carriers = Carrier.objects.filter(name=carrier,archived=False)
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
    if not hasattr(
        neo, "_LED_On_Control"
    ):  # iterative enabling for PTL from ATN via USB, see neo definition at the top
        for fs in free_slots:
            fs.led_state = 2
            fs.save()
            Thread(
                target=neo.led_on,
                kwargs={"lamp": fs.name, "color": "blue"},
            ).start()
            msg["slot"].append(fs.name)
    else:  # compound enabling for neotel rack
        neo._LED_On_Control({"lamps": {fs.name: "blue" for fs in free_slots}})
        free_slots.update(led_state=0)

    return JsonResponse(msg)


@csrf_exempt
def store_carrier_choose_slot_confirm(request, carrier, slot):
    # see store carrier choose slot

    carrier = carrier.strip()  # remove whitespace
    slot = slot.strip()  # remove whitespace
    queryset = Carrier.objects.filter(name=carrier,archived=False)
    if not queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})

    queryset2 = StorageSlot.objects.filter(qr_value=slot)
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
            "message": f"Carrier {c.name} stored in storage {ss.storage.name} slot {ss.qr_value}.",
        }
    )


@csrf_exempt
def store_carrier(request, carrier, storage):
    carrier = carrier.strip()  
    carriers = Carrier.objects.filter(name=carrier,archived=False)
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

    msg = {
        "storage": storage.name,
        "slot": fs.qr_value,
        "carrier": c.name,
        "success": True,
    }
    return JsonResponse(msg)


@csrf_exempt
def store_carrier_confirm(request, carrier, slot):
    # see store carrier

    carrier = carrier.strip()  # remove whitespace
    slot = slot.strip()  # remove whitespace
    queryset = Carrier.objects.filter(name=carrier,archived=False)
    if not queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})

    queryset2 = StorageSlot.objects.filter(qr_value=slot)
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
            "lamp": ss.name,
        },
    ).start()
    ss.save()
    return JsonResponse({"success": True})


def collect_carrier(request, carrier_name):
    """
    The user requests to collect a carrier. If possible, it's added to the collection "queue" (actually a set but queue sounds better),
    so the user can collect batchwise, not one by one. In the next step, the user scans all the carriers to ensure they collected the correct ones.
    """
    carrier_name = carrier_name.strip()
    requested_carrier = Carrier.objects.filter(name=carrier_name,archived=False).first()

    queued_carriers = Carrier.objects.filter(collecting=True,archived=False)  # collect queue

    if requested_carrier in queued_carriers:
        return JsonResponse({"success": False, "message": "Already in queue."})

    requested_carrier.collecting = True  # add to queue
    requested_carrier.save()

    queued_carriers = Carrier.objects.filter(collecting=True,archived=False)
    collection_queue = [
        {
            "carrier": queued_carrier.name,
            "storage": queued_carrier.storage_slot.storage.name,
            "slot": queued_carrier.storage_slot.qr_value,
        }
        for queued_carrier in queued_carriers
    ]

    response_message = {
        "storage": requested_carrier.storage_slot.storage.name,
        "slot": requested_carrier.storage_slot.qr_value,
        "carrier": requested_carrier.name,
        "queue": collection_queue,
    }

    requested_carrier.storage_slot.led_state = 2
    Thread(
        target=neo.led_on, kwargs={"lamp": requested_carrier.storage_slot.name, "color": "green"}
    ).start()

    return JsonResponse(response_message)


def collect_carrier_confirm(request, carrier, slot):
    carrier = carrier.strip()
    slot = slot.strip()

    queued_carrier = Carrier.objects.filter(collecting=True, name=carrier,archived=False).first()

    if not queued_carrier:
        return JsonResponse({"success": False, "message": f"Carrier {carrier} is not in the collect queue."})

    if queued_carrier.storage_slot.qr_value != slot:
        return JsonResponse(
            {"success": False,
             "message": f"Carrier {carrier} is in slot {queued_carrier.storage_slot.qr_value} not in slot {slot}"}
        )

    queued_carrier.storage_slot.led_state = 0
    queued_carrier.storage_slot.save()

    Thread(target=neo.led_off, kwargs={"lamp": queued_carrier.storage_slot.name}).start()

    queued_carrier.storage_slot = None
    queued_carrier.collecting = False
    queued_carrier.save()

    collection_queue = [
        {
            "carrier": qc.name,
            "storage": qc.storage_slot.storage.name,
            "slot": qc.storage_slot.qr_value,
        }
        for qc in Carrier.objects.filter(collecting=True,archived=False)
    ]

    response_message = {
        "success": True,
        "storage": None,
        "slot": None,
        "carrier": queued_carrier.name,
        "queue": collection_queue,
    }

    return JsonResponse(response_message)


@csrf_exempt
def save_file_and_get_headers(request):
    """
    first step of a 2 step workflow to create articles/carriers from a csv file
    this step saves the file for future processing and returns the headers of said csv file
    """
    if request.FILES and request.POST:
        lf = LocalFile.objects.create(
            file_object=File(request.FILES["file"]),
            upload_type=request.POST["upload_type"],
            delimiter=request.POST["delimiter"]
        )
        try:
            with open(lf.file_object.path, newline="") as f:
                csv_reader = csv.reader(f, delimiter=lf.delimiter)
                lf.headers = list(csv_reader.__next__())
                lf.save()
                if lf.upload_type == "article":
                    model_fields = [f.name for f in Article._meta.get_fields()]
                elif lf.upload_type == "carrier":
                    model_fields = [f.name for f in Carrier._meta.get_fields()]
                elif lf.upload_type == "board":
                    model_fields = ["article", "count"]
                    if "board_name" in request.POST.keys():
                        lf.board_name = request.POST["board_name"]
                        lf.save()
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
    """
    first of all i am sorry for this monster, feel free to refactor when bored
    this function is the abstraction for the user uploading csv files to create model instances with them,
    but the csv headers names do not have to correspond with
    """
    # the models field names, because the user creates a mapping from the csv header names to the models field names in the frontend

    if request.method == "POST":
        file_name = request.POST.get("file_name")

        lf = LocalFile.objects.get(name=file_name)

        map_json = json.loads(request.POST["map"])

        map_l = [
            (k, v) for k, v in map_json.items() if v
        ]  # remove fields that have empty values

        msg = {"created": [], "fail": []}

        with open(lf.file_object.path, 'r', encoding='ISO-8859-1') as f:

            csv_reader = csv.reader(f, delimiter=lf.delimiter)
            a_headers = next(csv_reader)

            index_map = {value: index for index, value in enumerate(a_headers)}
            map_ordered_l = sorted(map_l, key=lambda x: index_map[x[1]])

            for item in csv_reader:
                if lf.upload_type == "board":
                    if not lf.board_name or not Board.objects.filter(name=lf.board_name):
                        msg["fail"].append(f"Board {lf.board_name} does not exist.")
                        break
                    board = Board.objects.get(name=lf.board_name)

                    board_article_dict = {
                        key[0]: item[a_headers.index(key[1])] for key in map_ordered_l
                    }
                    board_article_dict["board"] = board

                    article_name = board_article_dict["article"]
                    article_exists = Article.objects.filter(name=article_name).exists()

                    if not article_exists:
                        article_count = board_article_dict.get("count")
                        if not article_count or not article_count.isnumeric():
                            msg["fail"].append(f"{article_name} has an invalid count.")
                            break

                        board_article_dict["name"] = f"{board.name}_{article_name}"
                        BoardArticle.objects.create(**board_article_dict)
                        msg["created"].append(board_article_dict["name"])

                elif lf.upload_type == "carrier":
                    carrier_dict = {
                        key[0]: item[a_headers.index(key[1])] for key in map_ordered_l
                    }

                    article_name = carrier_dict.get("article")
                    if article_name:
                        article = Article.objects.get(name=article_name)
                        carrier_dict["article"] = article

                    # Set default values if not provided
                    carrier_dict.setdefault("storage_slot", None)
                    carrier_dict.setdefault("storage", None)
                    carrier_dict.setdefault("machine_slot", None)
                    carrier_dict.setdefault("diameter", 7)
                    carrier_dict.setdefault("width", 8)

                    container_type = carrier_dict.get("container_type", "").lower()
                    carrier_dict["container_type"] = {
                        "reel": 0,
                        "tray": 1,
                        "bag": 2,
                        "single": 3
                    }.get(container_type, 0)

                    carrier_name = carrier_dict["name"]
                    if not Carrier.objects.filter(name=carrier_name).exists():
                        new_carrier = Carrier.objects.create(**carrier_dict)
                        msg["created"].append(new_carrier.name)
                    else:
                        msg["fail"].append(carrier_name)

                elif lf.upload_type == "article":
                    article_dict = {
                        key[0]: item[a_headers.index(key[1])] for key in map_ordered_l
                    }

                    manufacturer_name = article_dict.get("manufacturer")
                    if manufacturer_name:
                        manufacturer, manufacturer_created = Manufacturer.objects.get_or_create(name=manufacturer_name)
                        article_dict["manufacturer"] = manufacturer
                        if manufacturer_created:
                            msg["created"].append(manufacturer.name)

                    provider_keys = ["provider1", "provider2", "provider3", "provider4", "provider5"]
                    for provider_key in provider_keys:
                        if provider_key in article_dict and article_dict[provider_key]:
                            provider, provider_created = Provider.objects.get_or_create(name=article_dict[provider_key])
                            article_dict[provider_key] = provider
                            if provider_created:
                                msg["created"].append(provider.name)

                    if "boardarticle" in article_dict and article_dict["boardarticle"]:
                        del article_dict["boardarticle"]

                    article_name = article_dict["name"]
                    article_exists = Article.objects.filter(name=article_name).exists()

                    if not article_exists:
                        new_article = Article.objects.create(
                            **{key: value for key, value in article_dict.items() if key and value}
                        )

                        if new_article:
                            msg["created"].append(new_article.name)
                    else:
                        msg["fail"].append(article_name)

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


class BoardFilter(rest_filter.FilterSet):
    class Meta:
        model = Board
        fields = "__all__"


class BoardViewSet(viewsets.ModelViewSet):
    queryset = Board.objects.all()
    serializer_class = BoardSerializer
    filter_backends = (
        rest_filter.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_class = BoardFilter


class BoardArticleFilter(rest_filter.FilterSet):
    class Meta:
        model = BoardArticle
        fields = "__all__"


class BoardArticleViewSet(viewsets.ModelViewSet):
    queryset = BoardArticle.objects.all()
    serializer_class = BoardArticleSerializer
    filter_backends = (
        rest_filter.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_class = BoardArticleFilter


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
