from pprint import pp
from threading import Thread, Timer
from xml.sax.handler import feature_external_ges

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse


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
        carrier__isnull=True,
        storage=storage,
        diameter__gte=carrier.diameter,
        width__gte=carrier.width,
    )
    if not free_slots_queryset:
        return JsonResponse(
            {
                "success": False,
                "message": f"No free storage slot in Storage {storage_name}.",
            }
        )

    free_slot = free_slots_queryset.first()
    free_slot.led_state = 1

    # check if another carrier was nominated for this slot if yes clear it
    if hasattr(free_slot, "nominated_carrier"):
        other_carrier = free_slot.nominated_carrier
        free_slot.nominated_carrier.nominated_for_slot = None
        other_carrier.save()
    free_slot.save()

    carrier.nominated_for_slot = free_slot
    carrier.save()
    led_dispatcher = LED_shelf_dispatcher(
        Storage.objects.get(name=free_slot.storage.name)
    )
    Thread(
        target=led_dispatcher.led_on, kwargs={"lamp": free_slot.name, "color": "yellow"}
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
        target=dispatchers[slot.storage.name].led_on,
        kwargs={"lamp": slot.name, "color": "green"},
    ).start()
    Timer(
        interval=2,
        function=dispatchers[slot.storage.name].led_off,
        kwargs={"lamp": slot.name},
    ).start()

    return JsonResponse({"success": True})


# NEW FUNCTIONS FOR UPDATED WORKFLOW

def store_carrier_choose_slot_all_storages(request, carrier_name):
    """
    New endpoint for manual storage - lights up all available slots across ALL storages
    URL pattern: store_carrier_choose_slot_all_storages/<str:carrier_name>/
    """
    carrier_name = carrier_name.strip()

    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)

    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    
    carrier = carrier_queryset.first()
    
    # Same carrier validation as before
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

    # Find free slots across ALL storages that can fit this carrier
    free_slot_queryset = StorageSlot.objects.filter(
        carrier__isnull=True,
        diameter__gte=carrier.diameter,
        width__gte=carrier.width,
    ).select_related('storage')  # Optimize query
    
    if len(free_slot_queryset) == 0:
        return JsonResponse(
            {
                "success": False,
                "message": "No free storage slots found in any storage.",
            }
        )

    # Group slots by storage for the response
    slots_by_storage = {}
    all_storages = set()
    
    for slot in free_slot_queryset:
        storage_name = slot.storage.name
        if storage_name not in slots_by_storage:
            slots_by_storage[storage_name] = []
        slots_by_storage[storage_name].append(slot.qr_value)
        all_storages.add(slot.storage)

    msg = {
        "carrier": carrier.name,
        "slots_by_storage": slots_by_storage,
        "total_available_slots": len(free_slot_queryset),
        "success": True,
    }

    # Light up all available slots across all storages
    free_slot_queryset.update(led_state=1)

    # Start LED control threads for each storage
    for storage in all_storages:
        storage_slots = free_slot_queryset.filter(storage=storage)
        Thread(
            target=LED_shelf_dispatcher(storage)._LED_On_Control,
            kwargs={
                "lights_dict": {
                    "lamps": {
                        slot.name: "yellow" for slot in storage_slots
                    }
                }
            }
        ).start()

    return JsonResponse(msg)


@csrf_exempt
def store_carrier_choose_slot_confirm_by_qr(request, carrier_name, slot_qr):
    """
    Updated confirm endpoint - takes carrier and slot QR, automatically determines storage
    URL pattern: store_carrier_choose_slot_confirm_by_qr/<str:carrier_name>/<str:slot_qr>/
    """
    carrier_name = carrier_name.strip()
    slot_qr = slot_qr.strip()

    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()

    # Find slot by QR code (unique across all storages)
    slot_queryset = StorageSlot.objects.filter(qr_value=slot_qr).select_related('storage')
    if not slot_queryset:
        return JsonResponse({"success": False, "message": "Slot not found"})
    slot = slot_queryset.first()
    
    storage = slot.storage
    dispatcher = LED_shelf_dispatcher(storage)

    # Check if slot is occupied
    if hasattr(slot, "carrier") and slot.carrier:
        slot.led_state = 1
        slot.save()
        Thread(
            target=dispatcher.led_on,
            kwargs={"lamp": slot.name, "color": "red"},
        ).start()
        slot.led_state = 0
        slot.save()
        Timer(
            interval=2,
            function=dispatcher.led_off,
            kwargs={"lamp": slot.name},
        ).start()
        return JsonResponse(
            {
                "success": False,
                "message": f"Slot {slot.qr_value} is occupied by {slot.carrier.name}.",
            }
        )

    if slot.led_state == 0:
        return JsonResponse({"success": False, "message": "LED is off but shouldn't be"})

    # Store the carrier
    carrier.storage_slot = slot
    carrier.save()
    
    # Turn off all LEDs across all storages (reset all)
    StorageSlot.objects.all().update(led_state=0)
    
    # Reset LEDs for all storages that had slots lit up
    affected_storages = Storage.objects.all()
    print(f"rest for :{affected_storages}")
    
    for affected_storage in affected_storages:
        Thread(target=LED_shelf_dispatcher(affected_storage).reset_leds).start()

    # Show green confirmation on the selected slot
    slot.led_state = 1
    slot.save()
    Timer(
        interval=0.5,
        function=dispatcher.led_on,
        kwargs={"lamp": slot.name, "color": "green"},
    ).start()
    slot.led_state = 0
    slot.save()
    Timer(
        interval=4,
        function=dispatcher.led_off,
        kwargs={"lamp": slot.name},
    ).start()

    return JsonResponse(
        {
            "success": True,
            "message": f"Carrier {carrier.name} stored in {storage.name} slot {slot.qr_value}.",
            "storage": storage.name,
            "slot": slot.qr_value
        }
    )


def store_carrier_choose_slot_cancel_all(request, carrier_name):
    """
    Updated cancel endpoint - resets LEDs across ALL storages
    URL pattern: store_carrier_choose_slot_cancel_all/<str:carrier_name>/
    """
    # Turn off all LEDs across all storages
    StorageSlot.objects.all().update(led_state=0)
    
    # Reset lighthouse states for all storages
    Storage.objects.all().update(lighthouse_A_yellow=False, lighthouse_B_yellow=False)
    
    # Reset LEDs for all storages
    all_storages = Storage.objects.all()
    for storage in all_storages:
        dispatcher = LED_shelf_dispatcher(storage)
        Thread(target=dispatcher.reset_leds, kwargs={"working_light": True}).start()

    return JsonResponse({"success": True, "message": "Operation cancelled, all LEDs reset."})


# For auto storage - add storage selection step
def fetch_available_storages_for_auto(request):
    """
    New endpoint to fetch available storages for auto storage selection
    URL pattern: fetch_available_storages_for_auto/
    """
    storages = Storage.objects.filter(archived=False).values('name')
    return JsonResponse({
        "success": True,
        "storages": list(storages)
    })


def store_auto_with_storage_selection(request, carrier_name, storage_name):
    """
    Modified auto storage endpoint that requires storage selection first
    This would replace or supplement the existing auto storage endpoint
    URL pattern: store_auto_with_storage_selection/<str:carrier_name>/<str:storage_name>/
    """
    carrier_name = carrier_name.strip()
    storage_name = storage_name.strip()
    
    # Validate carrier (same as existing auto storage logic)
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    
    carrier = carrier_queryset.first()
    
    # Same carrier validation as manual storage
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
    
    # Validate storage
    storage_queryset = Storage.objects.filter(name=storage_name, archived=False)
    if not storage_queryset:
        return JsonResponse({"success": False, "message": "Storage not found."})
    
    storage = storage_queryset.first()
    
    # Continue with existing auto storage logic but for the selected storage
    # This calls the existing store_carrier function but with the selected storage
    return store_carrier(request, carrier_name, storage_name)


@csrf_exempt
def store_carrier_cancel(request, carrier_name):
    # see store carrier

    carrier_name = carrier_name.strip()

    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    carrier = carrier_queryset.first()

    slot = carrier.nominated_for_slot
    storage = slot.storage
    dispatchers = {storage.name: LED_shelf_dispatcher(storage)}

    carrier.nominated_for_slot = None
    carrier.save()

    slot.led_state = 0
    slot.save()

    Thread(
        target=dispatchers[slot.storage.name].led_on,
        kwargs={"lamp": slot.name, "color": "red"},
    ).start()
    Timer(
        interval=2,
        function=dispatchers[slot.storage.name].led_off,
        kwargs={"lamp": slot.name},
    ).start()

    return JsonResponse({"success": True})


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
        carrier__isnull=True,
        storage=storage,
        diameter__gte=carrier.diameter,
        width__gte=carrier.width,
    )
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

    free_slot_queryset.update(led_state=1)

    Thread(
        LED_shelf_dispatcher(storage)._LED_On_Control(
            {
                "lamps": {
                    free_slot.name: "yellow"
                    for free_slot in free_slot_queryset.filter(storage=storage)
                }
            }
        )
    ).start()

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

    storage = Storage.objects.filter(name=storage_name).first()
    dispatcher = LED_shelf_dispatcher(storage)

    if hasattr(slot, "carrier"):
        slot.led_state = 1
        slot.save()
        Thread(
            target=dispatcher.led_on,
            kwargs={"lamp": slot.name, "color": "red"},
        ).start()
        slot.led_state = 0
        slot.save()
        Timer(
            interval=2,
            function=dispatcher.led_off,
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
    print(f"CONFIRM CHOOSE SLOT START")
    Thread(target=dispatcher.reset_leds).start()
    print(f"CONFIRM CHOOSE SLOT END")
    StorageSlot.objects.filter(storage=storage).update(led_state=0)

    

    slot.led_state = 1
    slot.save()
    Timer(
        interval=0.5,
        function=dispatcher.led_on,
        kwargs={"lamp": slot.name, "color": "green"},
    ).start()
    slot.led_state = 0
    slot.save()
    Timer(
        interval=4,
        function=dispatcher.led_off,
        kwargs={"lamp": slot.name},
    ).start()

    

    return JsonResponse(
        {
            "success": True,
            "message": f"Carrier {carrier.name} stored in storage {slot.storage.name} slot {slot.qr_value}.",
        }
    )


def store_carrier_choose_slot_cancel(request, carrier_name, storage_name):
    StorageSlot.objects.filter(storage=storage_name).update(led_state=0)
    storage = Storage.objects.filter(name=storage_name)
    storage.update(lighthouse_A_yellow=False, lighthouse_B_yellow=False)
    dispatcher = LED_shelf_dispatcher(storage.first())
    Thread(target=dispatcher.reset_leds, kwargs={"working_light": True}).start()

    return JsonResponse({"success": True})


@csrf_exempt
def store_carrier_collect_and_store(request, carrier_name, storage_name):
    """
    Endpoint for carriers that are already stored - collects them first, then stores in new location
    URL pattern: store_carrier_collect_and_store/<str:carrier_name>/<str:storage_name>/
    """
    carrier_name = carrier_name.strip()
    storage_name = storage_name.strip()

    # Validate carrier
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    
    carrier = carrier_queryset.first()
    
    # Basic validations (but allow already stored carriers)
    if carrier.collecting:
        return JsonResponse({"success": False, "message": "Carrier is collecting."})
    if carrier.archived:
        return JsonResponse({"success": False, "message": "Carrier has been archived."})
    if not carrier.delivered:
        return JsonResponse({"success": False, "message": "Carrier has not been delivered."})
    if carrier.machine_slot:
        return JsonResponse({"success": False, "message": f"Carrier is in Machine Slot {carrier.machine_slot.name}."})

    # Store the old slot for cleanup (if carrier is already stored)
    old_slot = carrier.storage_slot
    
    # Validate new storage
    storage_queryset = Storage.objects.filter(name=storage_name)
    if not storage_queryset:
        return JsonResponse({"success": False, "message": f"No such storage {storage_name}."})
    storage = storage_queryset.first()

    # Find available slots in new storage
    free_slots_queryset = StorageSlot.objects.filter(
        carrier__isnull=True,
        storage=storage,
        diameter__gte=carrier.diameter,
        width__gte=carrier.width,
    )
    if not free_slots_queryset:
        return JsonResponse({"success": False, "message": f"No free storage slot in Storage {storage_name}."})

    # If carrier was already stored, collect it first (without LED effects to avoid confusion)
    if old_slot:
        carrier.storage_slot = None
        carrier.save()

    # Now proceed with normal storing logic
    free_slot = free_slots_queryset.first()
    free_slot.led_state = 1

    # Check if another carrier was nominated for this slot, if yes clear it
    if hasattr(free_slot, "nominated_carrier"):
        other_carrier = free_slot.nominated_carrier
        free_slot.nominated_carrier.nominated_for_slot = None
        other_carrier.save()
    free_slot.save()

    carrier.nominated_for_slot = free_slot
    carrier.save()
    
    led_dispatcher = LED_shelf_dispatcher(storage)
    Thread(
        target=led_dispatcher.led_on, 
        kwargs={"lamp": free_slot.name, "color": "yellow"}
    ).start()

    msg = {
        "storage": storage.name,
        "slot": free_slot.qr_value,
        "carrier": carrier.name,
        "success": True,
        "was_relocated": old_slot is not None,
        "old_location": f"{old_slot.storage.name}/{old_slot.qr_value}" if old_slot else None
    }
    return JsonResponse(msg)


@csrf_exempt  
def store_carrier_choose_slot_collect_and_store(request, carrier_name, storage_name):
    """
    Manual slot selection version for carriers that are already stored
    URL pattern: store_carrier_choose_slot_collect_and_store/<str:carrier_name>/<str:storage_name>/
    """
    carrier_name = carrier_name.strip()
    storage_name = storage_name.strip()

    # Validate carrier
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    
    carrier = carrier_queryset.first()
    
    # Basic validations (but allow already stored carriers)
    if carrier.collecting:
        return JsonResponse({"success": False, "message": "Carrier is collecting."})
    if carrier.archived:
        return JsonResponse({"success": False, "message": "Carrier has been archived."})
    if not carrier.delivered:
        return JsonResponse({"success": False, "message": "Carrier has not been delivered."})
    if carrier.machine_slot:
        return JsonResponse({"success": False, "message": f"Carrier is in Machine Slot {carrier.machine_slot.name}."})

    # Store old slot for reference
    old_slot = carrier.storage_slot
    
    # Validate new storage
    storage_queryset = Storage.objects.filter(name=storage_name)
    if not storage_queryset:
        return JsonResponse({"success": False, "message": "No storage found."})
    storage = storage_queryset.first()

    # Find available slots in new storage
    free_slot_queryset = StorageSlot.objects.filter(
        carrier__isnull=True,
        storage=storage,
        diameter__gte=carrier.diameter,
        width__gte=carrier.width,
    )
    if len(free_slot_queryset) == 0:
        return JsonResponse({"success": False, "message": f"No free storage slots found in {storage.name}."})

    # If carrier was already stored, collect it first (silently)
    if old_slot:
        carrier.storage_slot = None
        carrier.save()

    # Light up available slots in the new storage
    free_slot_queryset.update(led_state=1)
    
    Thread(
        target=LED_shelf_dispatcher(storage)._LED_On_Control,
        args=[{
            "lamps": {
                free_slot.name: "yellow" for free_slot in free_slot_queryset.filter(storage=storage)
            }
        }]
    ).start()

    msg = {
        "storage": storage.name,
        "carrier": carrier.name,
        "slot": [free_slot.qr_value for free_slot in free_slot_queryset],
        "success": True,
        "was_relocated": old_slot is not None,
        "old_location": f"{old_slot.storage.name}/{old_slot.qr_value}" if old_slot else None
    }

    return JsonResponse(msg)


@csrf_exempt
def store_carrier_collect_and_store(request, carrier_name, storage_name):
    """
    Endpoint for carriers that are already stored - collects them first, then stores in new location
    URL pattern: store_carrier_collect_and_store/<str:carrier_name>/<str:storage_name>/
    """
    carrier_name = carrier_name.strip()
    storage_name = storage_name.strip()

    # Validate carrier
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    
    carrier = carrier_queryset.first()
    
    # Basic validations (but allow already stored carriers)
    if carrier.collecting:
        return JsonResponse({"success": False, "message": "Carrier is collecting."})
    if carrier.archived:
        return JsonResponse({"success": False, "message": "Carrier has been archived."})
    if not carrier.delivered:
        return JsonResponse({"success": False, "message": "Carrier has not been delivered."})
    if carrier.machine_slot:
        return JsonResponse({"success": False, "message": f"Carrier is in Machine Slot {carrier.machine_slot.name}."})

    # Store the old slot for cleanup (if carrier is already stored)
    old_slot = carrier.storage_slot
    
    # Validate new storage
    storage_queryset = Storage.objects.filter(name=storage_name)
    if not storage_queryset:
        return JsonResponse({"success": False, "message": f"No such storage {storage_name}."})
    storage = storage_queryset.first()

    # Find available slots in new storage
    free_slots_queryset = StorageSlot.objects.filter(
        carrier__isnull=True,
        storage=storage,
        diameter__gte=carrier.diameter,
        width__gte=carrier.width,
    )
    if not free_slots_queryset:
        return JsonResponse({"success": False, "message": f"No free storage slot in Storage {storage_name}."})

    # If carrier was already stored, collect it first (without LED effects to avoid confusion)
    if old_slot:
        carrier.storage_slot = None
        carrier.save()

    # Now proceed with normal storing logic
    free_slot = free_slots_queryset.first()
    free_slot.led_state = 1

    # Check if another carrier was nominated for this slot, if yes clear it
    if hasattr(free_slot, "nominated_carrier"):
        other_carrier = free_slot.nominated_carrier
        free_slot.nominated_carrier.nominated_for_slot = None
        other_carrier.save()
    free_slot.save()

    carrier.nominated_for_slot = free_slot
    carrier.save()
    
    led_dispatcher = LED_shelf_dispatcher(storage)
    Thread(
        target=led_dispatcher.led_on, 
        kwargs={"lamp": free_slot.name, "color": "yellow"}
    ).start()

    msg = {
        "storage": storage.name,
        "slot": free_slot.qr_value,
        "carrier": carrier.name,
        "success": True,
        "was_relocated": old_slot is not None,
        "old_location": f"{old_slot.storage.name}/{old_slot.qr_value}" if old_slot else None
    }
    return JsonResponse(msg)


@csrf_exempt  
def store_carrier_choose_slot_collect_and_store(request, carrier_name, storage_name):
    """
    Manual slot selection version for carriers that are already stored
    URL pattern: store_carrier_choose_slot_collect_and_store/<str:carrier_name>/<str:storage_name>/
    """
    carrier_name = carrier_name.strip()
    storage_name = storage_name.strip()

    # Validate carrier
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    
    carrier = carrier_queryset.first()
    
    # Basic validations (but allow already stored carriers)
    if carrier.collecting:
        return JsonResponse({"success": False, "message": "Carrier is collecting."})
    if carrier.archived:
        return JsonResponse({"success": False, "message": "Carrier has been archived."})
    if not carrier.delivered:
        return JsonResponse({"success": False, "message": "Carrier has not been delivered."})
    if carrier.machine_slot:
        return JsonResponse({"success": False, "message": f"Carrier is in Machine Slot {carrier.machine_slot.name}."})

    # Store old slot for reference
    old_slot = carrier.storage_slot
    
    # Validate new storage
    storage_queryset = Storage.objects.filter(name=storage_name)
    if not storage_queryset:
        return JsonResponse({"success": False, "message": "No storage found."})
    storage = storage_queryset.first()

    # Find available slots in new storage
    free_slot_queryset = StorageSlot.objects.filter(
        carrier__isnull=True,
        storage=storage,
        diameter__gte=carrier.diameter,
        width__gte=carrier.width,
    )
    if len(free_slot_queryset) == 0:
        return JsonResponse({"success": False, "message": f"No free storage slots found in {storage.name}."})

    # If carrier was already stored, collect it first (silently)
    if old_slot:
        carrier.storage_slot = None
        carrier.save()

    # Light up available slots in the new storage
    free_slot_queryset.update(led_state=1)
    
    Thread(
        target=LED_shelf_dispatcher(storage)._LED_On_Control,
        args=[{
            "lamps": {
                free_slot.name: "yellow" for free_slot in free_slot_queryset.filter(storage=storage)
            }
        }]
    ).start()

    msg = {
        "storage": storage.name,
        "carrier": carrier.name,
        "slot": [free_slot.qr_value for free_slot in free_slot_queryset],
        "success": True,
        "was_relocated": old_slot is not None,
        "old_location": f"{old_slot.storage.name}/{old_slot.qr_value}" if old_slot else None
    }

    return JsonResponse(msg)


# NEW COLLECT-AND-STORE FUNCTIONS

@csrf_exempt
def store_carrier_collect_and_store(request, carrier_name, storage_name):
    """
    Endpoint for carriers that are already stored - collects them first, then stores in new location
    URL pattern: store_carrier_collect_and_store/<str:carrier_name>/<str:storage_name>/
    """
    carrier_name = carrier_name.strip()
    storage_name = storage_name.strip()

    # Validate carrier
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    
    carrier = carrier_queryset.first()
    
    # Basic validations (but allow already stored carriers)
    if carrier.collecting:
        return JsonResponse({"success": False, "message": "Carrier is collecting."})
    if carrier.archived:
        return JsonResponse({"success": False, "message": "Carrier has been archived."})
    if not carrier.delivered:
        return JsonResponse({"success": False, "message": "Carrier has not been delivered."})
    if carrier.machine_slot:
        return JsonResponse({"success": False, "message": f"Carrier is in Machine Slot {carrier.machine_slot.name}."})

    # Store the old slot for cleanup (if carrier is already stored)
    old_slot = carrier.storage_slot
    
    # Validate new storage
    storage_queryset = Storage.objects.filter(name=storage_name)
    if not storage_queryset:
        return JsonResponse({"success": False, "message": f"No such storage {storage_name}."})
    storage = storage_queryset.first()

    # Find available slots in new storage
    free_slots_queryset = StorageSlot.objects.filter(
        carrier__isnull=True,
        storage=storage,
        diameter__gte=carrier.diameter,
        width__gte=carrier.width,
    )
    if not free_slots_queryset:
        return JsonResponse({"success": False, "message": f"No free storage slot in Storage {storage_name}."})

    # If carrier was already stored, collect it first (without LED effects to avoid confusion)
    if old_slot:
        carrier.storage_slot = None
        carrier.save()

    # Now proceed with normal storing logic
    free_slot = free_slots_queryset.first()
    free_slot.led_state = 1

    # Check if another carrier was nominated for this slot, if yes clear it
    if hasattr(free_slot, "nominated_carrier"):
        other_carrier = free_slot.nominated_carrier
        free_slot.nominated_carrier.nominated_for_slot = None
        other_carrier.save()
    free_slot.save()

    carrier.nominated_for_slot = free_slot
    carrier.save()
    
    led_dispatcher = LED_shelf_dispatcher(storage)
    Thread(
        target=led_dispatcher.led_on, 
        kwargs={"lamp": free_slot.name, "color": "yellow"}
    ).start()

    msg = {
        "storage": storage.name,
        "slot": free_slot.qr_value,
        "carrier": carrier.name,
        "success": True,
        "was_relocated": old_slot is not None,
        "old_location": f"{old_slot.storage.name}/{old_slot.qr_value}" if old_slot else None
    }
    return JsonResponse(msg)


@csrf_exempt  
def store_carrier_choose_slot_collect_and_store(request, carrier_name, storage_name):
    """
    Manual slot selection version for carriers that are already stored
    URL pattern: store_carrier_choose_slot_collect_and_store/<str:carrier_name>/<str:storage_name>/
    """
    carrier_name = carrier_name.strip()
    storage_name = storage_name.strip()

    # Validate carrier
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    
    carrier = carrier_queryset.first()
    
    # Basic validations (but allow already stored carriers)
    if carrier.collecting:
        return JsonResponse({"success": False, "message": "Carrier is collecting."})
    if carrier.archived:
        return JsonResponse({"success": False, "message": "Carrier has been archived."})
    if not carrier.delivered:
        return JsonResponse({"success": False, "message": "Carrier has not been delivered."})
    if carrier.machine_slot:
        return JsonResponse({"success": False, "message": f"Carrier is in Machine Slot {carrier.machine_slot.name}."})

    # Store old slot for reference
    old_slot = carrier.storage_slot
    
    # Validate new storage
    storage_queryset = Storage.objects.filter(name=storage_name)
    if not storage_queryset:
        return JsonResponse({"success": False, "message": "No storage found."})
    storage = storage_queryset.first()

    # Find available slots in new storage
    free_slot_queryset = StorageSlot.objects.filter(
        carrier__isnull=True,
        storage=storage,
        diameter__gte=carrier.diameter,
        width__gte=carrier.width,
    )
    if len(free_slot_queryset) == 0:
        return JsonResponse({"success": False, "message": f"No free storage slots found in {storage.name}."})

    # If carrier was already stored, collect it first (silently)
    if old_slot:
        carrier.storage_slot = None
        carrier.save()

    # Light up available slots in the new storage
    free_slot_queryset.update(led_state=1)
    
    Thread(
        target=LED_shelf_dispatcher(storage)._LED_On_Control,
        args=[{
            "lamps": {
                free_slot.name: "yellow" for free_slot in free_slot_queryset.filter(storage=storage)
            }
        }]
    ).start()

    msg = {
        "storage": storage.name,
        "carrier": carrier.name,
        "slot": [free_slot.qr_value for free_slot in free_slot_queryset],
        "success": True,
        "was_relocated": old_slot is not None,
        "old_location": f"{old_slot.storage.name}/{old_slot.qr_value}" if old_slot else None
    }

    return JsonResponse(msg)
