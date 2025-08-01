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

    # TODO check if the carrier is already in the collect queue
    # TODO add carrier to the collect queue

    # Turn on the LED for the carrier's storage slot.
    carrier.storage_slot.led_state = 1
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
    # TODO handle collecting status of carrier
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
    slot.led_state = 1
    slot.save()

    carrier.storage_slot = None
    carrier.save()

    led_dispatcher = LED_shelf_dispatcher(slot.storage)
    Thread(
        target=led_dispatcher.led_on, kwargs={"lamp": slot.name, "color": "green"}
    ).start()
    slot.led_state = 0
    slot.save()
    Timer(
        interval=2,
        function=led_dispatcher.led_off,
        kwargs={"lamp": slot.name},
    ).start()

    return JsonResponse({"success": True})


def collect_single_carrier_cancel(request, carrier_name):
    # TODO handle collecting status of carrier
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

    # turn off LED
    slot = carrier.storage_slot

    slot.led_state = 1
    slot.save()

    led_dispatcher = LED_shelf_dispatcher(slot.storage)
    Thread(
        target=led_dispatcher.led_on, kwargs={"lamp": slot.name, "color": "red"}
    ).start()
    slot.led_state = 0
    slot.save()
    Timer(
        interval=2,
        function=led_dispatcher.led_off,
        kwargs={"lamp": slot.name},
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
    carrier.storage_slot.led_state = 1
    carrier.storage_slot.save()

    led_dispatcher = LED_shelf_dispatcher(carrier.storage_slot.storage)

    Thread(
        target=led_dispatcher.led_on,
        kwargs={"lamp": carrier.storage_slot.name, "color": "blue"},
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
        "success": True,
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

    led_dispatcher = LED_shelf_dispatcher(carrier.storage_slot.storage)
    carrier.storage_slot.led_state = 1
    carrier.storage_slot.save()

    Thread(
        target=led_dispatcher.led_on, kwargs={"lamp": slot.name, "color": "green"}
    ).start()
    carrier.storage_slot.led_state = 0
    carrier.storage_slot.save()

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

    # If this is the last carrier to be collected from this storage then turn off the yellow workinglight
    collect_queue_queryset = Carrier.objects.filter(collecting=True, archived=False)
    
    # Check if there are any more carriers being collected from this storage
    remaining_carriers_in_storage = collect_queue_queryset.filter(
        storage_slot__storage=turned_off_slot.storage
    ).count()
    
    # If no more carriers are being collected from this storage, update working lights based on LED state
    if remaining_carriers_in_storage == 0:
        Thread(
            target=led_dispatcher.enable_working_lights_based_on_led_state
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


def collect_carrier_cancel(request, carrier_name):

    # Strip leading and trailing whitespace
    carrier_name = carrier_name.strip()

    # Look up the carrier in the database.
    carrier_queryset = Carrier.objects.filter(name=carrier_name)

    carrier = carrier_queryset.first()

    slot = carrier.storage_slot

    # Turn off the LED for the carrier's storage slot.

    led_dispatcher = LED_shelf_dispatcher(carrier.storage_slot.storage)
    carrier.storage_slot.led_state = 1
    carrier.storage_slot.save()
    Thread(
        target=led_dispatcher.led_on, kwargs={"lamp": slot.name, "color": "red"}
    ).start()
    carrier.storage_slot.led_state = 0
    carrier.storage_slot.save()
    Timer(
        interval=2,
        function=led_dispatcher.led_off,
        kwargs={"lamp": slot.name},
    ).start()

    carrier.collecting = False
    carrier.save()

    # Check if there are any more carriers being collected from this storage
    remaining_carriers_in_storage = Carrier.objects.filter(
        collecting=True, 
        archived=False,
        storage_slot__storage=slot.storage
    ).count()

    # If no more carriers are being collected from this storage, update working lights based on LED state
    if remaining_carriers_in_storage == 0:
        Thread(
            target=led_dispatcher.enable_working_lights_based_on_led_state
        ).start()

    collect_queue_queryset = Carrier.objects.filter(collecting=True, archived=False)

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
    Lights up only the first carrier's slot to avoid confusion.

    Args:
    - request: HTTP request object
    - article: Article number to collect

    Returns:
    - JsonResponse indicating success or failure
    """
    article_name = article_name.strip()
    slot_queryset = StorageSlot.objects.filter(
        carrier__article__name=article_name,
        carrier__archived=False,
        carrier__collecting=False,
    ).order_by('id')  # Ensure consistent ordering

    if not slot_queryset:
        return JsonResponse(
            {
                "success": False,
                "message": f"Could not find a carrier with article {article_name} in any storage",
            }
        )

    # Light up only the FIRST carrier's slot in yellow to guide the operator
    first_slot = slot_queryset.first()
    first_slot.led_state = 1
    first_slot.save()

    led_dispatcher = LED_shelf_dispatcher(first_slot.storage)
    Thread(
        target=led_dispatcher.led_on,
        kwargs={"lamp": first_slot.name, "color": "yellow"},
    ).start()

    return JsonResponse({"success": True})


def collect_carrier_by_article_confirm(request, carrier_name):
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
    # TODO handle collecting status of carriers
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

    storages = Storage.objects.all()
    dispatchers = {storage.name: LED_shelf_dispatcher(storage) for storage in storages}
    # Update LED state for all storage slots to off
    StorageSlot.objects.update(led_state=0)

    # Reset LEDs after carrier confirmation
    for storage in storages:
        Thread(target=dispatchers[storage.name].reset_leds).start()
        # Update working lights based on LED state for this storage
        Thread(
            target=dispatchers[storage.name].enable_working_lights_based_on_led_state
        ).start()

    collected_slot.led_state = 1
    collected_slot.save()
    # turn on collected_slot for a short duration
    Thread(
        target=dispatchers[collected_slot.storage.name].led_on,
        kwargs={"lamp": collected_slot.name, "color": "green"},
    ).start()
    collected_slot.led_state = 0
    collected_slot.save()
    Timer(
        interval=2,
        function=dispatchers[collected_slot.storage.name].led_off,
        kwargs={"lamp": collected_slot.name},
    ).start()

    return JsonResponse({"success": True})


def collect_carrier_by_article_cancel(request, article_name):
    # TODO handle collecting status of carriers
    # get all slots that are turned on and have carrier with article_name and filter down to list of storages that need to be reset
    stored_carriers_with_article = Carrier.objects.filter(
        article__name=article_name, storage_slot__isnull=False
    )

    slot_ids = stored_carriers_with_article.values_list("storage_slot__pk", flat=True)
    slot_queryset = StorageSlot.objects.filter(pk__in=slot_ids)

    storage_names = slot_queryset.values_list("storage", flat=True).distinct()
    storages = Storage.objects.filter(pk__in=storage_names)

    dispatchers = {storage.name: LED_shelf_dispatcher(storage) for storage in storages}
    # Update LED state for all storage slots to off
    slot_queryset.update(led_state=0)
    # Reset LEDs and update working lights based on LED state
    for storage in storages:
        Thread(target=dispatchers[storage.name].reset_leds).start()
        # Update working lights based on LED state for this storage
        Thread(
            target=dispatchers[storage.name].enable_working_lights_based_on_led_state
        ).start()

    return JsonResponse({"success": True})


def collect_carrier_by_article_select(request, article_name, carrier_name):
    """
    Selects a specific carrier from the article collection, highlighting only that carrier's slot.
    """
    article_name = article_name.strip()
    carrier_name = carrier_name.strip()
    
    # First reset all LEDs for this article
    stored_carriers_with_article = Carrier.objects.filter(
        article__name=article_name, 
        storage_slot__isnull=False,
        archived=False
    )
    
    slot_ids = stored_carriers_with_article.values_list("storage_slot__pk", flat=True)
    slot_queryset = StorageSlot.objects.filter(pk__in=slot_ids)
    
    storage_names = slot_queryset.values_list("storage", flat=True).distinct()
    storages = Storage.objects.filter(pk__in=storage_names)
    dispatchers = {storage.name: LED_shelf_dispatcher(storage) for storage in storages}
    
    # Reset all LEDs first
    slot_queryset.update(led_state=0)
    for storage in storages:
        Thread(target=dispatchers[storage.name].reset_leds).start()
    
    # Find the specific carrier and light it up yellow
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    
    carrier = carrier_queryset.first()
    if not carrier.storage_slot:
        return JsonResponse({"success": False, "message": "Carrier is not stored."})
    
    # Light up only the selected carrier's slot in yellow
    carrier.storage_slot.led_state = 1
    carrier.storage_slot.save()
    
    led_dispatcher = LED_shelf_dispatcher(carrier.storage_slot.storage)
    Thread(
        target=led_dispatcher.led_on,
        kwargs={"lamp": carrier.storage_slot.name, "color": "yellow"}
    ).start()
    
    return JsonResponse({"success": True})


def collect_job(request, job_name):
    # TODO handle collecting status of carriers
    job_name = job_name.strip()

    job_queryset = Job.objects.filter(name=job_name, archived=False)
    if not job_queryset:
        return JsonResponse({"success": False, "message": "Job does not exist"})

    job = job_queryset.first()
    if job.status == 0:
        return JsonResponse({"success": False, "message": "Job is not fully prepared."})
    if job.status == 2:
        return JsonResponse({"success": False, "message": "Job is already complete."})

    stored_carriers_of_job = job.carriers.filter(storage_slot__isnull=False)

    number_of_carriers_of_job = job.carriers.all().count()
    number_of_stored_carriers_of_job = stored_carriers_of_job.count()

    storage_names = stored_carriers_of_job.values_list(
        "storage_slot__storage__name", flat=True
    ).distinct()

    storages = Storage.objects.filter(pk__in=storage_names)
    dispatchers = {storage.name: LED_shelf_dispatcher(storage) for storage in storages}

    stored_carriers_of_job.update(collecting=True)

    slot_ids = stored_carriers_of_job.values_list("storage_slot__id", flat=True)
    slots = StorageSlot.objects.filter(pk__in=slot_ids)
    slots.update(led_state=1)
    slots_by_storage = {
        storage: list(slots.filter(Q(storage=storage))) for storage in storages
    }

    for storage, slots_in_that_storage in slots_by_storage.items():
        Thread(
            target=dispatchers[storage.name]._LED_On_Control,
            kwargs={
                "lights_dict": {
                    "lamps": {slot.name: "blue" for slot in slots_in_that_storage}
                }
            },
        ).start()
    return JsonResponse(
        {
            "success": True,
            "message": (
                f"Not all Carriers of this job are stored! {number_of_stored_carriers_of_job} carriers to be collected."
                if number_of_stored_carriers_of_job != number_of_carriers_of_job
                else f"{number_of_carriers_of_job} carriers to be collected."
            ),
        }
    )
