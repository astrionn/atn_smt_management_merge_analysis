from threading import Thread, Timer

from django.http import JsonResponse
from django.db.models import Q

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

from .utils.led_shelf_dispatcher import LED_shelf_dispatcher


def collect_single_carrier(request, carrier_name):
    """Collects a single carrier by name, turning on its LED and returning related information.

    Args:
        request: The Django HTTP request object.
        carrier_name: The name of the carrier to collect.

    Returns:
        A JsonResponse with the following fields:
            success: True if the carrier was collected successfully, False otherwise.
            message: An error message if success is False, otherwise empty.
            carrier: The name of the collected carrier.
            slot: The QR code value of the carrier's storage slot.
            storage: The name of the storage unit where the carrier is located.
    """

    # Strip leading and trailing whitespace from the carrier name.
    carrier_name = carrier_name.strip()

    # Look up the carrier in the database.
    carrier_queryset = Carrier.objects.filter(name=carrier_name)

    # Check if the carrier exists, is not archvived and is stored
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()

    if carrier.archived:
        return JsonResponse({"success": False, "message": "Carrier has been archived."})

    if not carrier.storage_slot:
        return JsonResponse({"success": False, "message": "Carrier is not stored."})

    # Turn on the LED for the carrier's storage slot.
    carrier.storage_slot.led_state = 2
    carrier.storage_slot.save()

    Thread(
        target=LED_shelf_dispatcher(carrier.storage_slot.storage).led_on,
        kwargs={"lamp": carrier.storage_slot.name, "color": "blue"},
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
    """Confirms the collection of a single carrier by clearing its associated storage slot and controlling LEDs

    Args:
        request: The Django HTTP request object.
        carrier_name: The name of the carrier to collect.

    Returns:
        A JsonResponse with the following fields:
            success: True if the carrier was collected successfully, False otherwise.
            message: An error message if success is False, otherwise empty.
    """

    # Strip leading and trailing whitespace from the carrier name.
    carrier_name = carrier_name.strip()

    # Look up the carrier in the database.
    carrier_queryset = Carrier.objects.filter(name=carrier_name)

    # Check if the carrier exists and is not archvied
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()

    if carrier.archived:
        return JsonResponse({"success": False, "message": "Carrier has been archived."})

    # Clear the carrier's storage slot and turn off LED and working_light
    slot = carrier.storage_slot
    slot.carrier = None
    slot.led_state = 0
    slot.save()

    led_dispatcher = LED_shelf_dispatcher(slot.storage)
    Thread(
        target=led_dispatcher.led_on, kwargs={"lamp": slot.name, "color": "green"}
    ).start()
    Timer(
        interval=2,
        function=led_dispatcher.led_off,
        kwargs={"lamp": slot.name},
    ).start()

    # TODO instead of hardcoding the 700 we should base it on the storage capacity
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
    Endpoint for collecting a carrier. If possible, it's added to the collection "queue" (actually a set but 'queue' is a better term),
    allowing users to collect carriers batchwise rather than one by one. In the subsequent step, users can scan all the carriers to ensure they collected the correct ones.

    Args:
        request: The Django HTTP request object.
        carrier_name : The name of the carrier to be collected.

    Returns:
        JsonResponse: A JSON response indicating the success or failure of the operation, along with relevant messages and the current collection queue.
    """

    # Strip leading and trailing whitespace from the carrier name.
    carrier_name = carrier_name.strip()

    # Check if the carrier exists, is not archvived is stored and not already in the collect queue
    carrier_queryset = Carrier.objects.filter(name=carrier_name)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()

    if carrier.archived:
        return JsonResponse({"success": False, "message": "Carrier has been archived."})

    if not carrier.storage_slot:
        return JsonResponse({"success": False, "message": f"Carrier is not stored."})

    if carrier.collecting:
        return JsonResponse({"success": False, "message": "Already in queue."})

    # add carrier to the queue
    carrier.collecting = True
    carrier.save()

    # turn on the LED
    carrier.storage_slot.led_state = 2
    carrier.storage_slot.save()

    led_dispatcher = LED_shelf_dispatcher(carrier.storage_slot.storage)

    Thread(
        target=led_dispatcher.led_on,
        kwargs={"lamp": carrier.storage_slot.name, "color": "green"},
    ).start()

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

    return JsonResponse(response_message)


def collect_carrier_confirm(request, carrier_name, storage_name, slot_name):

    # Strip leading and trailing whitespace
    carrier_name = carrier_name.strip()
    storage_name = storage_name.strip()
    slot_name = slot_name.strip()

    # Look up the carrier in the database.
    carrier_queryset = Carrier.objects.filter(name=carrier_name)

    # Check if the carrier exists, is not archvived and is not already in the queue
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()

    if carrier.archived:
        return JsonResponse({"success": False, "message": "Carrier has been archived."})

    if not carrier.collecting:
        return JsonResponse(
            {
                "success": False,
                "message": f"Carrier {carrier} is not in the collect queue.",
            }
        )

    # Look up the storage slot in the database.
    slot_queryset = StorageSlot.objects.filter(qr_value=slot_name, storage=storage_name)

    if not slot_queryset:
        return JsonResponse(
            {"success": False, "message": f"Slot {slot_name} not found."}
        )
    slot = slot_queryset.first()

    # Check if the carrier is in the provided slot
    if carrier.storage_slot.qr_value != slot.qr_value:
        return JsonResponse(
            {
                "success": False,
                "message": f"Carrier {carrier.name} is in slot {carrier.storage_slot.qr_value} not in slot {slot.qr_value}",
            }
        )

    # Turn off the LED for the carrier's storage slot.
    carrier.storage_slot.led_state = 0
    carrier.storage_slot.save()

    led_dispatcher = LED_shelf_dispatcher(carrier.storage_slot.storage)

    # TODO maybe change slot color for short interval before turning off
    Thread(
        target=led_dispatcher.led_on, kwargs={"lamp": slot.name, "color": "green"}
    ).start()
    Timer(
        interval=2,
        function=led_dispatcher.led_off,
        kwargs={"lamp": slot.name},
    ).start()

    # Clear the carriers storage slot
    turned_off_slot = carrier.storage_slot

    carrier.storage_slot = None
    carrier.collecting = False
    carrier.save()

    # If this is the last carrier to be collected from this side of this storage then turn off the yellow workinglight
    collect_queue_queryset = Carrier.objects.filter(collecting=True, archived=False)

    storage_slots_same_side_as_turned_off_slot = [
        carrier.storage_slot
        for carrier in collect_queue_queryset
        if (turned_off_slot.name <= 700 and carrier.storage_slot.name <= 700)
        or (turned_off_slot.name > 700 and carrier.storage_slot.name > 700)
    ]
    if not storage_slots_same_side_as_turned_off_slot:
        # TODO turn on the green working_light again
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
                    "lamps": {slot.name: "blue" for slot in slots_in_that_storage}
                }
            },
        )
    return JsonResponse({"success": True})
