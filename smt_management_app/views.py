import json
import csv
import io
import qrcode
from threading import Thread, Timer
from pprint import pprint as pp


from django_filters.rest_framework import DjangoFilterBackend
from django.middleware.csrf import get_token
from django.views.decorators.csrf import requires_csrf_token, csrf_exempt
from django_filters import rest_framework as rest_filter
import django_filters
from django.http import FileResponse, JsonResponse
from django.core.files import File
from rest_framework import viewsets, filters, generics
from django.db.models import Q

from django.conf import settings
from .utils.led_shelf_dispatcher import LED_shelf_dispatcher
from .serializers import (
    ArticleNameSerializer,
    ArticleSerializer,
    BoardArticleSerializer,
    BoardSerializer,
    CarrierNameSerializer,
    CarrierSerializer,
    JobSerializer,
    MachineSerializer,
    MachineSlotSerializer,
    ManufacturerNameSerializer,
    ManufacturerSerializer,
    ProviderNameSerializer,
    ProviderSerializer,
    StorageSerializer,
    StorageSlotSerializer,
)
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


try:
    # initalize 3rd party handlers for connected devices like smart shelfs and label printers

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
    carrier_object = Carrier.objects.filter(name=carrier, archived=False).first()

    if job_object and carrier_object:
        job_object.carriers.add(carrier_object)
        if len(job_object.carriers) == len(job_object.board.articles):
            job_object.status = 1
        job_object.save()
        return JsonResponse({"success": True})
    else:
        return JsonResponse({"success": False})


@csrf_exempt
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
        carrier_obj = Carrier.objects.get(name=carrier, archived=False)
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
    storage_queryset = Storage.objects.all()
    for storage in storage_queryset:
        led_dispatcher = LED_shelf_dispatcher(storage)
        Thread(
            target=led_dispatcher.test_leds(),
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
    carriers_in_production = Carrier.objects.filter(
        archived=False, storage_slot__isnull=True, delivered=True
    ).count()
    free_slots = StorageSlot.objects.filter(carrier__isnull=True).count()
    active_storages = Storage.objects.filter(archived=False).count()
    total_finished_jobs = Job.objects.filter(status=2).count()
    open_jobs_created = Job.objects.filter(archived=False, status=0).count()
    open_jobs_finished = Job.objects.filter(archived=False, status=2).count()

    return JsonResponse(
        {
            "total_carriers": total_carriers,
            "not_delivered": undelivered_carriers,
            "in_storage": carriers_in_storage,
            "in_production": carriers_in_production,
            "free_slots": free_slots,
            "storages": active_storages,
            "total_finished_jobs": total_finished_jobs,
            "open_jobs_created": open_jobs_created,
            "open_jobs_prepared": open_jobs_created,
            "open_jobs_finished": open_jobs_finished,
        }
    )


def collect_carrier_by_article(request, article_name):
    """
    Collects a carrier by article from a storage unit.
    Lights up slots containing the specified article.

    Args:
    - request: HTTP request object
    - article: Article number to collect

    Returns:
    - JsonResponse indicating success or failure
    """
    article_name = article_name.strip()
    slot_queryset = StorageSlot.objects.filter(
        carrier__article__name=article_name, carrier__archived=False
    )

    if not slot_queryset:
        return JsonResponse(
            {
                "success": False,
                "message": f"Could not find a carrier with article {article_name} in any storage",
            }
        )

    # Activate LEDs for slots containing the article
    # refactor with _LED_On_Control to enable all at once

    storage_names = slot_queryset.values_list("storage", flat=True).distinct()
    storages = Storage.objects.filter(pk__in=storage_names)
    dispatchers = {storage.name: LED_shelf_dispatcher(storage) for storage in storages}
    for slot in slot_queryset:
        Thread(
            target=dispatchers[slot.storage.name].led_on,
            kwargs={"lamp": slot.name, "color": "blue"},
        ).start()

    return JsonResponse({"success": True})


def confirm_carrier_by_article(request, carrier_name):
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
    carrier_name = carrier_name.strip()
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()

    slot_queryset = StorageSlot.objects.filter(carrier=carrier)

    if not slot_queryset:
        return JsonResponse(
            {
                "success": False,
                "message": f"Could not find a slot in that contains carrier {carrier_name}.",
            }
        )

    collected_slot = carrier.storage_slot
    carrier.storage_slot = None
    carrier.storage = None
    carrier.save()

    slot_queryset = StorageSlot.objects.filter(led_state=2)
    storage_names = slot_queryset.values_list("storage", flat=True).distinct()
    storages = Storage.objects.filter(pk__in=storage_names)
    dispatchers = {storage.name: LED_shelf_dispatcher(storage) for storage in storages}
    # Reset LEDs after carrier confirmation
    for storage in storages:
        Thread(target=dispatchers[storage.name].reset_leds).start()
        Thread(
            target=dispatchers[storage.name]._LED_On_Control,
            kwargs={"lights_dict": {"status": {"A": "green", "B": "green"}}},
        ).start()

    # Update LED state for all storage slots to off
    slot_queryset.update(led_state=0)

    # turn on collected_slot for a short duration
    Thread(
        target=dispatchers[collected_slot.storage.name].led_on,
        kwargs={"lamp": collected_slot.name, "color": "green"},
    ).start()
    Timer(
        interval=2,
        function=dispatchers[collected_slot.storage.name].led_off,
        kwargs={"lamp": collected_slot.name},
    ).start()

    return JsonResponse({"success": True})


@csrf_exempt
def reset_leds(request, storage_name):
    """
    Resets LEDs and updates the LED state of storage slots.

    Args:
    - request: HTTP request object.
    - storage: Storage information.

    Returns:
    - JsonResponse: JSON response indicating LED reset status.
    """
    storage = Storage.objects.get(name=storage_name)
    led_dispatcher = LED_shelf_dispatcher(storage)
    # Start a new thread to reset LEDs with working_light set to True
    Thread(target=led_dispatcher.reset_leds, kwargs={"working_light": True}).start()
    Thread(
        taraget=led_dispatcher._LED_On_Control,
        kwargs={"lights_dict": {"status": {"A": "green", "B": "green"}}},
    )
    # Update LED state for all storage slots to 0
    StorageSlot.objects.filter(storage=storage).update(led_state=0)

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
def store_carrier_choose_slot(request, carrier_name, storage_name):
    carrier_name = carrier_name.strip()
    storage_name = storage_name.strip()

    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)

    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()
    if carrier.collecting:
        return JsonResponse({"success": False, "message": "Carrier is collecting."})
    if carrier.archived:
        return JsonResponse({"success": False, "message": "Carrier has been archived."})
    if not carrier.delivered:
        return JsonResponse(
            {"success": False, "message": "Carrier has not been delivered."}
        )
    if carrier.storage_slot:
        return JsonResponse({"success": False, "message": "Carrier is stored already."})
    if carrier.machine_slot:
        return JsonResponse({"success": False})

    storage_queryset = Storage.objects.filter(name=storage_name)
    if not storage_queryset:
        return JsonResponse({"success": False, "message": "No storage found."})
    storage = storage_queryset.first()

    free_slot_queryset = StorageSlot.objects.filter(
        carrier__isnull=True, storage=storage
    )  # later on take carrier size into consideration here
    if len(free_slot_queryset) == 0:
        return JsonResponse(
            {
                "success": False,
                "message": f"No free storage slots found in {storage.name}.",
            }
        )
    msg = {
        "storage": storage.name,
        "carrier": carrier.name,
        "slot": [free_slot.qr_value for free_slot in free_slot_queryset],
        "success": True,
    }

    storage_names = free_slot_queryset.values_list("storage", flat=True).distinct()
    storages = Storage.objects.filter(pk__in=storage_names)
    dispatchers = {storage.name: LED_shelf_dispatcher(storage) for storage in storages}
    for storage in storages:
        Thread(
            dispatchers[storage.name]._LED_On_Control(
                {
                    "lamps": {
                        free_slot.name: "blue"
                        for free_slot in free_slot_queryset.filter(storage=storage)
                    }
                }
            )
        ).start()
    free_slot_queryset.update(led_state=2)

    return JsonResponse(msg)


@csrf_exempt
def store_carrier_choose_slot_confirm(request, carrier_name, storage_name, slot_name):
    # see store carrier choose slot

    carrier_name = carrier_name.strip()
    slot_name = slot_name.strip()
    storage_name = storage_name.strip()

    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()

    slot_queryset = StorageSlot.objects.filter(qr_value=slot_name, storage=storage_name)
    if not slot_queryset:
        return JsonResponse({"success": False, "message": "no slot found"})
    slot = slot_queryset.first()

    storages = Storage.objects.all()
    dispatchers = {storage.name: LED_shelf_dispatcher(storage) for storage in storages}

    if hasattr(slot, "carrier"):
        Thread(
            target=dispatchers[slot.storage.name].led_on,
            kwargs={"lamp": slot.name, "color": "red"},
        ).start()
        Timer(
            interval=2,
            function=dispatchers[slot.storage.name].led_off,
            kwargs={"lamp": slot.name},
        ).start()
        return JsonResponse(
            {
                "success": False,
                "message": f"Slot {slot.qr_value} should contain {slot.carrier.name}.",
            }
        )

    if slot.led_state == 0:
        return JsonResponse({"success": False, "message": "led is off but shouldn't"})

    carrier.storage_slot = slot
    carrier.save()
    for storage in storages:
        Thread(target=dispatchers[storage.name].reset_leds).start()
        Thread(
            target=dispatchers[storage.name]._LED_On_Control,
            kwargs={"lights_dict": {"status": {"A": "green", "B": "green"}}},
        ).start()

    Thread(
        target=dispatchers[slot.storage.name].led_on,
        kwargs={"lamp": slot.name, "color": "green"},
    ).start()
    Timer(
        interval=2,
        function=dispatchers[slot.storage.name].led_off,
        kwargs={"lamp": slot.name},
    ).start()

    StorageSlot.objects.all().update(led_state=0)

    return JsonResponse(
        {
            "success": True,
            "message": f"Carrier {carrier.name} stored in storage {slot.storage.name} slot {slot.qr_value}.",
        }
    )


@csrf_exempt
def store_carrier(request, carrier_name, storage_name):
    carrier_name = carrier_name.strip()
    storage_name = storage_name.strip()

    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()
    if carrier.collecting:
        return JsonResponse({"success": False, "message": "Carrier is collecting."})
    if carrier.archived:
        return JsonResponse({"success": False, "message": "Carrier has been archived."})
    if not carrier.delivered:
        return JsonResponse(
            {"success": False, "message": "Carrier has not been delivered."}
        )
    if carrier.storage_slot:
        return JsonResponse(
            {
                "success": False,
                "message": f"Carrier is stored already({carrier.storage_slot.qr_value}).",
            }
        )
    if carrier.machine_slot:
        return JsonResponse(
            {
                "success": False,
                "message": f"Carrier is in Machine Slot {carrier.machine_slot.name}.",
            }
        )

    storage_queryset = Storage.objects.filter(name=storage_name)
    if not storage_queryset:
        return JsonResponse(
            {"success": False, "message": f"No such storage {storage_name}."}
        )
    storage = storage_queryset.first()

    free_slots_queryset = StorageSlot.objects.filter(
        carrier__isnull=True, storage=storage
    )  # later on take carrier size into consideration here
    if not free_slots_queryset:
        return JsonResponse(
            {
                "success": False,
                "message": f"No free storage slot in Storage {storage_name}.",
            }
        )

    free_slot = free_slots_queryset.first()
    free_slot.led_state = 2
    free_slot.save()
    carrier.nominated_for_slot = free_slot
    carrier.save()
    led_dispatcher = LED_shelf_dispatcher(
        Storage.objects.get(name=free_slot.storage.name)
    )
    Thread(
        target=led_dispatcher.led_on, kwargs={"lamp": free_slot.name, "color": "blue"}
    ).start()

    msg = {
        "storage": storage.name,
        "slot": free_slot.qr_value,
        "carrier": carrier.name,
        "success": True,
    }
    return JsonResponse(msg)


@csrf_exempt
def store_carrier_confirm(request, carrier_name, storage_name, slot_name):
    # see store carrier

    carrier_name = carrier_name.strip()
    storage_name = storage_name.strip()
    slot_name = slot_name.strip()

    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()

    slot_queryset = StorageSlot.objects.filter(qr_value=slot_name, storage=storage_name)
    if not slot_queryset:
        return JsonResponse({"success": False, "message": "Slot not found."})
    slot = slot_queryset.first()

    dispatchers = {
        storage.name: LED_shelf_dispatcher(storage)
        for storage in set([carrier.nominated_for_slot.storage, slot.storage])
    }
    if not carrier.nominated_for_slot == slot:
        Thread(
            target=dispatchers[slot.storage.name].led_on,
            kwargs={"lamp": slot.name, "color": "red"},
        ).start()
        Timer(
            interval=2,
            function=dispatchers[slot.storage.name].led_off,
            kwargs={"lamp": slot.name},
        ).start()
        return JsonResponse(
            {
                "sucess": False,
                "message": f"Scanned wrong slot {slot.qr_value} instead of slot {carrier.nominated_for_slot.qr_value}.",
            }
        )

    if slot.led_state == 0:
        return JsonResponse({"success": False, "message": "led is off but shouldn't"})

    carrier.storage_slot = slot
    carrier.nominated_for_slot = None
    carrier.save()
    slot.led_state = 0
    slot.save()

    Thread(
        target=dispatchers[slot.storage.name].led_off,
        kwargs={
            "lamp": slot.name,
        },
    ).start()

    Thread(
        target=dispatchers[slot.storage.name]._LED_Off_Control,
        kwargs={
            "statusA": True if int(slot.name) <= 700 else False,
            "statusB": False if int(slot.name) <= 700 else True,
        },
    ).start()

    for storage_name in dispatchers.keys():
        Thread(
            target=dispatchers[storage_name]._LED_On_Control,
            kwargs={"lights_dict": {"status": {"A": "green", "B": "green"}}},
        ).start()
    return JsonResponse({"success": True})


def collect_job(request, job_name):
    job_name = job_name.strip()

    job_queryset = Job.objects.filter(name=job_name, archived=False)
    if not job_queryset:
        return JsonResponse({"success": False, "message": "Job does not exist"})

    job = job_queryset.first()
    if job.status == 0:
        return JsonResponse({"success": False, "message": "Job is not fully prepared."})
    if job.status == 2:
        return JsonResponse({"success": False, "message": "Job is already complete."})

    carriers_of_job = job.carriers.all()
    storage_names = carriers_of_job.values_list(
        "storage_slot__storage__name", flat=True
    ).distinct()

    storages = Storage.objects.filter(pk__in=storage_names)
    dispatchers = {storage.name: LED_shelf_dispatcher(storage) for storage in storages}

    carriers_of_job.update(collecting=True)

    slot_ids = carriers_of_job.values_list("storage_slot__id", flat=True)
    slots = StorageSlot.objects.filter(pk__in=slot_ids)
    slots_by_storage = {
        storage: list(slots.filter(Q(storage=storage))) for storage in storages
    }

    for carrier in carriers_of_job:
        carrier.storage_slot.led_state = 2
        carrier.save()

    for storage, slots_in_that_storage in slots_by_storage.items():
        Thread(
            target=dispatchers[storage.name]._LED_On_Control,
            kwargs={
                "lights_dict": {
                    "lamps": {slot.name: "yellow" for slot in slots_in_that_storage}
                }
            },
        )
    return JsonResponse({"success": True})


def collect_single_carrier(request, carrier_name):

    carrier_name = carrier_name.strip()
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()

    if not carrier.storage_slot:
        return JsonResponse({"success": False, "message": "Carrier is not stored."})
    carrier.storage_slot.led_state = 2
    carrier.storage_slot.save()

    Thread(
        target=LED_shelf_dispatcher(carrier.storage_slot.storage).led_on,
        kwargs={"lamp": carrier.storage_slot.name, "color": "green"},
    ).start()

    return JsonResponse(
        {
            "success": True,
            "carrier": carrier.name,
            "slot": carrier.storage_slot.qr_value,
            "storage": carrier.storage_slot.storage.name,
        }
    )


def collect_single_carrier_confirm(request, carrier_name):

    carrier_name = carrier_name.strip()
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()
    slot = carrier.storage_slot

    slot.carrier = None
    slot.led_state = 0
    slot.save()

    led_dispatcher = LED_shelf_dispatcher(slot.storage)
    Thread(target=led_dispatcher.led_off, kwargs={"lamp": slot.name}).start()

    Thread(
        target=led_dispatcher._LED_Off_Control,
        kwargs={
            "statusA": True if int(slot.name) <= 700 else False,
            "statusB": False if int(slot.name) <= 700 else True,
        },
    ).start()
    return JsonResponse({"success": True})


def collect_carrier(request, carrier_name):
    """
    The user requests to collect a carrier. If possible, it's added to the collection "queue" (actually a set but queue sounds better),
    so the user can collect batchwise, not one by one. In the next step, the user scans all the carriers to ensure they collected the correct ones.
    """
    carrier_name = carrier_name.strip()
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()

    if not carrier.storage_slot:
        return JsonResponse({"success": False, "message": f"Carrier is not stored."})

    if carrier.collecting:
        return JsonResponse({"success": False, "message": "Already in queue."})

    carrier.collecting = True  # add to queue
    carrier.save()

    queued_carriers = Carrier.objects.filter(collecting=True, archived=False)
    collection_queue = [
        {
            "carrier": queued_carrier.name,
            "storage": queued_carrier.storage_slot.storage.name,
            "slot": queued_carrier.storage_slot.qr_value,
        }
        for queued_carrier in queued_carriers
    ]

    response_message = {
        "storage": carrier.storage_slot.storage.name,
        "slot": carrier.storage_slot.qr_value,
        "carrier": carrier.name,
        "queue": collection_queue,
    }

    carrier.storage_slot.led_state = 2
    carrier.storage_slot.save()

    led_dispatcher = LED_shelf_dispatcher(carrier.storage_slot.storage)

    Thread(
        target=led_dispatcher.led_on,
        kwargs={"lamp": carrier.storage_slot.name, "color": "green"},
    ).start()

    return JsonResponse(response_message)


def collect_carrier_confirm(request, carrier_name, storage_name, slot_name):
    carrier_name = carrier_name.strip()
    storage_name = storage_name.strip()
    slot_name = slot_name.strip()

    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()

    if not carrier.collecting:
        return JsonResponse(
            {
                "success": False,
                "message": f"Carrier {carrier} is not in the collect queue.",
            }
        )

    slot_queryset = StorageSlot.objects.filter(qr_value=slot_name, storage=storage_name)
    if not slot_queryset:
        return JsonResponse(
            {"success": False, "message": f"Slot {slot_name} not found."}
        )
    slot = slot_queryset.first()

    if carrier.storage_slot.qr_value != slot.qr_value:
        return JsonResponse(
            {
                "success": False,
                "message": f"Carrier {carrier.name} is in slot {carrier.storage_slot.qr_value} not in slot {slot.qr_value}",
            }
        )

    carrier.storage_slot.led_state = 0
    carrier.storage_slot.save()

    led_dispatcher = LED_shelf_dispatcher(carrier.storage_slot.storage)

    Thread(
        target=led_dispatcher.led_off, kwargs={"lamp": carrier.storage_slot.name}
    ).start()

    turned_off_slot = carrier.storage_slot

    carrier.storage_slot = None
    carrier.collecting = False
    carrier.save()

    collect_queue_queryset = Carrier.objects.filter(collecting=True, archived=False)

    storage_slots_same_side_as_turned_off_slot = [
        carrier.storage_slot
        for carrier in collect_queue_queryset
        if (turned_off_slot.name <= 700 and carrier.storage_slot.name <= 700)
        or (turned_off_slot.name > 700 and carrier.storage_slot.name > 700)
    ]
    if not storage_slots_same_side_as_turned_off_slot:
        Thread(
            target=led_dispatcher._LED_Off_Control,
            kwargs={
                "statusA": True if turned_off_slot.name <= 700 else False,
                "statusB": False if turned_off_slot.name <= 700 else True,
            },
        ).start()

    collect_queue = [
        {
            "carrier": carrier.name,
            "storage": carrier.storage_slot.storage.name,
            "slot": carrier.storage_slot.qr_value,
        }
        for carrier in collect_queue_queryset
    ]

    response_message = {
        "success": True,
        "storage": None,
        "slot": None,
        "carrier": carrier.name,
        "queue": collect_queue,
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
            delimiter=request.POST["delimiter"],
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

        with open(lf.file_object.path, "r", encoding="ISO-8859-1") as f:

            csv_reader = csv.reader(f, delimiter=lf.delimiter)
            a_headers = next(csv_reader)

            index_map = {value: index for index, value in enumerate(a_headers)}
            map_ordered_l = sorted(map_l, key=lambda x: index_map[x[1]])

            for item in csv_reader:
                if lf.upload_type == "board":
                    if not lf.board_name or not Board.objects.filter(
                        name=lf.board_name
                    ):
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

                        article = Article.objects.filter(name=article_name).first()
                        if article:
                            carrier_dict["article"] = article
                        else:
                            msg["fail"].append(article_name)
                            continue

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
                        "single": 3,
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
                        manufacturer, manufacturer_created = (
                            Manufacturer.objects.get_or_create(name=manufacturer_name)
                        )
                        article_dict["manufacturer"] = manufacturer
                        if manufacturer_created:
                            msg["created"].append(manufacturer.name)

                    provider_keys = [
                        "provider1",
                        "provider2",
                        "provider3",
                        "provider4",
                        "provider5",
                    ]
                    for provider_key in provider_keys:
                        if provider_key in article_dict and article_dict[provider_key]:
                            provider, provider_created = Provider.objects.get_or_create(
                                name=article_dict[provider_key]
                            )
                            article_dict[provider_key] = provider
                            if provider_created:
                                msg["created"].append(provider.name)

                    if "boardarticle" in article_dict and article_dict["boardarticle"]:
                        del article_dict["boardarticle"]

                    article_name = article_dict["name"]
                    article_exists = Article.objects.filter(name=article_name).exists()

                    if not article_exists:
                        new_article = Article.objects.create(
                            **{
                                key: value
                                for key, value in article_dict.items()
                                if key and value
                            }
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
            Q(provider1__name__contains=value)
            | Q(provider2__name__contains=value)
            | Q(provider3__name__contains=value)
            | Q(provider4__name__contains=value)
            | Q(provider5__name__contains=value)
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
            Q(article__provider1__name__contains=value)
            | Q(article__provider2__name__contains=value)
            | Q(article__provider3__name__contains=value)
            | Q(article__provider4__name__contains=value)
            | Q(article__provider5__name__contains=value)
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
