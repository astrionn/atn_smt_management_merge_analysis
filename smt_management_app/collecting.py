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
from .helpers import find_slot_by_qr_code, slot_matches_qr_code


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

    # FIXED: Filter out carriers without storage_slot
    queued_carriers = Carrier.objects.filter(
        collecting=True, archived=False, storage_slot__isnull=False
    )
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

    # Look up the storage slot using combined slots support
    slot = find_slot_by_qr_code(slot_name, storage_name)

    if not slot:
        return JsonResponse(
            {"success": False, "message": f"Slot {slot_name} not found."}
        )

    # Check if the carrier is in the provided slot (using combined slots support)
    if not slot_matches_qr_code(carrier.storage_slot, slot_name):
        return JsonResponse(
            {
                "success": False,
                "message": f"Carrier {carrier.name} is in slot {carrier.storage_slot.qr_value} not in slot {slot_name}",
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

    # FIXED: Build queue BEFORE clearing storage_slot
    # Get current queue before modifications
    collect_queue_queryset = Carrier.objects.filter(
        collecting=True, archived=False, storage_slot__isnull=False
    ).exclude(
        pk=carrier.pk
    )  # Exclude current carrier

    collect_queue = [
        {
            "carrier": c.name,
            "storage": c.storage_slot.storage.name,
            "slot": c.storage_slot.qr_value,
        }
        for c in collect_queue_queryset
    ]

    # Clear the carriers storage slot
    turned_off_slot = carrier.storage_slot

    carrier.storage_slot = None
    carrier.collecting = False
    carrier.save()

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

    # FIXED: Filter out carriers without storage_slot
    collect_queue_queryset = Carrier.objects.filter(
        collecting=True, archived=False, storage_slot__isnull=False
    )

    collect_queue = [
        {
            "carrier": c.name,
            "storage": c.storage_slot.storage.name,
            "slot": c.storage_slot.qr_value,
        }
        for c in collect_queue_queryset
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
        carrier__article__name=article_name,
        carrier__archived=False,
        carrier__collecting=False,
    )

    if not slot_queryset:
        return JsonResponse(
            {
                "success": False,
                "message": f"Could not find a carrier with article {article_name} in any storage",
            }
        )

    # Activate LEDs for slots containing the article

    # TODO mark carriers as collecting

    storage_names = slot_queryset.values_list("storage", flat=True).distinct()
    storages = Storage.objects.filter(pk__in=storage_names)
    dispatchers = {storage.name: LED_shelf_dispatcher(storage) for storage in storages}
    slots_by_storage = {storage.name: [] for storage in storages}

    for slot in slot_queryset:
        slots_by_storage[slot.storage.name].append(slot)

    for storage_name, slots in slots_by_storage.items():
        lights_dict = {"lamps": {slot.name: "blue" for slot in slots}}
        StorageSlot.objects.filter(id__in=[slot.id for slot in slots]).update(
            led_state=1
        )
        Thread(
            target=dispatchers[storage_name]._LED_On_Control,
            kwargs={"lights_dict": lights_dict},
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


def collect_carrier_by_article_select(request, article_name, carrier_name, led_state):
    """
    Selects a specific carrier from the article collection, highlighting only that carrier's slot.
    """
    article_name = article_name.strip()
    carrier_name = carrier_name.strip()
    led_state = led_state.strip() == "true"
    # Find the specific carrier
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()
    if not carrier.storage_slot:
        return JsonResponse({"success": False, "message": "Carrier is not stored."})
    # Light up or turn off the selected carrier's slot
    carrier.storage_slot.led_state = int(led_state)
    carrier.storage_slot.save()
    led_dispatcher = LED_shelf_dispatcher(carrier.storage_slot.storage)
    if led_state:
        Thread(
            target=led_dispatcher.led_on,
            kwargs={"lamp": carrier.storage_slot.name, "color": "yellow"},
        ).start()
    else:
        Thread(
            target=led_dispatcher.led_off,
            kwargs={"lamp": carrier.storage_slot.name},
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
    # Reset LEDs
    for storage in storages:
        Thread(target=dispatchers[storage.name].reset_leds).start()

    return JsonResponse({"success": True})


def collect_carrier_by_article_select(request, article_name, carrier_name, led_state):
    """
    Selects/deselects a specific carrier for collection by article.
    Controls the LED state for individual carriers within the article collection modal.
    Supports merged slots feature.

    Args:
        request: The Django HTTP request object.
        article_name: The name of the article.
        carrier_name: The name of the carrier to select/deselect.
        led_state: 'true' to turn on LED and select, 'false' to turn off LED and deselect.

    Returns:
        JsonResponse indicating success or failure with carrier and LED state info.
    """
    
    article_name = article_name.strip()
    carrier_name = carrier_name.strip()
    led_state = led_state.strip().lower()
    
    # Validate led_state parameter
    if led_state not in ['true', 'false']:
        return JsonResponse({
            "success": False, 
            "message": "Invalid LED state. Must be 'true' or 'false'."
        })
    
    # Check if the carrier exists and is not archived
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset.exists():
        return JsonResponse({
            "success": False,
            "message": f"Carrier {carrier_name} not found or is archived."
        })
    
    carrier = carrier_queryset.first()
    
    # Check if carrier has the specified article
    if not carrier.article or carrier.article.name != article_name:
        return JsonResponse({
            "success": False,
            "message": f"Carrier {carrier_name} does not contain article {article_name}."
        })
    
    # Check if carrier is stored
    if not carrier.storage_slot:
        return JsonResponse({
            "success": False,
            "message": f"Carrier {carrier_name} is not stored."
        })
    
    # Check if carrier is already being collected
    if carrier.collecting:
        return JsonResponse({
            "success": False,
            "message": f"Carrier {carrier_name} is already in collection queue."
        })
    
    # Get the storage slot and LED dispatcher
    slot = carrier.storage_slot
    led_dispatcher = LED_shelf_dispatcher(slot.storage)
    
    # Handle LED state change
    if led_state == 'true':
        # Turn on LED (select carrier)
        slot.led_state = 1
        slot.save()
        
        Thread(
            target=led_dispatcher.led_on,
            kwargs={"lamp": slot.name, "color": "blue"}
        ).start()
        
        response_message = {
            "success": True,
            "message": f"Selected carrier {carrier_name}",
            "carrier": carrier_name,
            "article": article_name,
            "storage": slot.storage.name,
            "slot": slot.qr_value,
            "led_state": True,
            "selected": True
        }
        
    else:  # led_state == 'false'
        # Turn off LED (deselect carrier)
        slot.led_state = 0
        slot.save()
        
        Thread(
            target=led_dispatcher.led_off,
            kwargs={"lamp": slot.name}
        ).start()
        
        response_message = {
            "success": True,
            "message": f"Deselected carrier {carrier_name}",
            "carrier": carrier_name,
            "article": article_name,
            "storage": slot.storage.name,
            "slot": slot.qr_value,
            "led_state": False,
            "selected": False
        }
    
    return JsonResponse(response_message)


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
