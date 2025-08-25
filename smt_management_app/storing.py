from pprint import pp
from threading import Thread, Timer
from xml.sax.handler import feature_external_ges

from django.views.decorators.csrf import csrf_exempt
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


def get_truly_free_slots(storage, min_diameter, min_width):
    """
    Get slots that are free AND all their related slots in combined slots are free.

    Args:
        storage: Storage instance
        min_diameter: Minimum diameter requirement
        min_width: Minimum width requirement

    Returns:
        List of StorageSlot instances that are truly free (including their combined slots)
    """
    # Step 1: Get all potentially free slots that meet requirements
    potentially_free = list(
        StorageSlot.objects.filter(
            carrier__isnull=True,
            storage=storage,
            diameter__gte=min_diameter,
            width__gte=min_width,
        ).select_related("storage")
    )

    # Step 2: Collect all slot names that need checking in one batch
    all_names_to_check = set()
    slot_to_related_names = {}

    for slot in potentially_free:
        related_names = set(slot.get_all_slot_names())
        all_names_to_check.update(related_names)
        slot_to_related_names[slot.id] = related_names

    # Step 3: Check all occupied slots in a single query
    occupied_slots = set(
        StorageSlot.objects.filter(
            storage=storage, name__in=list(all_names_to_check), carrier__isnull=False
        ).values_list("name", flat=True)
    )

    # Step 4: Filter the truly free slots (no related occupied slots)
    truly_free = []
    for slot in potentially_free:
        related_names = slot_to_related_names[slot.id]
        if not occupied_slots.intersection(related_names):
            truly_free.append(slot)

    return truly_free


def is_combined_slot_occupied(slot):
    """
    Check if ANY slot in the combined group is occupied.

    Args:
        slot: StorageSlot instance

    Returns:
        bool: True if any slot in the combined group is occupied
    """
    all_slot_names = slot.get_all_slot_names()
    related_slots = StorageSlot.objects.filter(
        storage=slot.storage, name__in=all_slot_names
    )
    return related_slots.filter(carrier__isnull=False).exists()


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

    # Use combined-slot-aware free slot detection
    free_slots = get_truly_free_slots(storage, carrier.diameter, carrier.width)
    if not free_slots:
        return JsonResponse(
            {
                "success": False,
                "message": f"No free storage slot in Storage {storage_name}.",
            }
        )

    free_slot = free_slots[0]  # Get first truly free slot
    free_slot.led_state = 1

    # check if another carrier was nominated for this slot if yes clear it
    if hasattr(free_slot, "nominated_carrier") and free_slot.nominated_carrier:
        other_carrier = free_slot.nominated_carrier
        other_carrier.nominated_for_slot = None
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

    # Use combined slots support for QR lookup
    slot = find_slot_by_qr_code(slot_name, storage_name)
    if not slot:
        return JsonResponse({"success": False, "message": "Slot not found."})

    dispatchers = {
        storage.name: LED_shelf_dispatcher(storage)
        for storage in set([carrier.nominated_for_slot.storage, slot.storage])
    }

    # Check if scanned slot matches nominated slot (using combined slots support)
    if not slot_matches_qr_code(carrier.nominated_for_slot, slot_name):
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
                "message": f"Scanned wrong slot {slot_name} instead of slot {carrier.nominated_for_slot.qr_value}.",
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

    # Use combined-slot-aware free slot detection
    print(f"Searching for free slots in {storage.name} for carrier {carrier.name}")
    free_slots = get_truly_free_slots(storage, carrier.diameter, carrier.width)
    print(
        f"Found {len(free_slots)} free slots in {storage.name} for carrier {carrier.name}"
    )
    if len(free_slots) == 0:
        return JsonResponse(
            {
                "success": False,
                "message": f"No free storage slots found in {storage.name}.",
            }
        )

    msg = {
        "storage": storage.name,
        "carrier": carrier.name,
        "slot": [free_slot.qr_value for free_slot in free_slots],
        "success": True,
    }

    # Update LED state for all free slots
    free_slot_ids = [slot.id for slot in free_slots]
    StorageSlot.objects.filter(id__in=free_slot_ids).update(led_state=1)

    # Light up all related LEDs for combined slots
    lights_dict = {"lamps": {}}
    for free_slot in free_slots:
        # Add all related slot LEDs for combined slots
        all_names = free_slot.get_all_slot_names()
        for name in all_names:
            lights_dict["lamps"][name] = "yellow"

    Thread(
        target=LED_shelf_dispatcher(storage)._LED_On_Control,
        kwargs={"lights_dict": lights_dict},
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

    # Use combined slots support for QR lookup
    slot = find_slot_by_qr_code(slot_name, storage_name)
    if not slot:
        return JsonResponse({"success": False, "message": "no slot found"})

    storage = Storage.objects.filter(name=storage_name).first()
    dispatcher = LED_shelf_dispatcher(storage)

    # Check if ANY slot in the combined group is occupied
    if is_combined_slot_occupied(slot):
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

        # Find which specific slot in the group is occupied for error message
        occupied_slot = None
        all_slot_names = slot.get_all_slot_names()
        related_slots = StorageSlot.objects.filter(
            storage=slot.storage, name__in=all_slot_names, carrier__isnull=False
        )
        if related_slots.exists():
            occupied_slot = related_slots.first()

        error_msg = f"Slot {slot_name} is part of a combined slot group where "
        if (
            occupied_slot
            and hasattr(occupied_slot, "carrier")
            and occupied_slot.carrier
        ):
            error_msg += (
                f"slot {occupied_slot.name} contains {occupied_slot.carrier.name}."
            )
        else:
            error_msg += "another slot is occupied."

        return JsonResponse(
            {
                "success": False,
                "message": error_msg,
            }
        )

    if slot.led_state == 0:
        return JsonResponse({"success": False, "message": "led is off but shouldn't"})

    carrier.storage_slot = slot
    carrier.save()
    StorageSlot.objects.filter(storage=storage).update(led_state=0)

    Thread(target=dispatcher.reset_leds).start()

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
            "message": f"Carrier {carrier.name} stored in storage {slot.storage.name} slot {slot_name}.",
        }
    )


@csrf_exempt
def store_carrier_choose_slot_confirm_by_qr(request, carrier_name, slot_name):
    """
    Confirm slot selection using QR code without requiring storage name.
    Automatically finds the storage from the QR code.

    Args:
        request: Django request object
        carrier_name: Name of the carrier to store
        slot_name: QR code of the slot

    Returns:
        JsonResponse with success status and message
    """
    carrier_name = carrier_name.strip()
    slot_name = slot_name.strip()

    # Find carrier
    carrier_queryset = Carrier.objects.filter(name=carrier_name, archived=False)
    if not carrier_queryset:
        return JsonResponse({"success": False, "message": "Carrier not found."})
    carrier = carrier_queryset.first()

    # Find slot by QR code across all storages
    slot = None
    for storage in Storage.objects.all():
        found_slot = find_slot_by_qr_code(slot_name, storage.name)
        if found_slot:
            slot = found_slot
            break

    if not slot:
        return JsonResponse(
            {
                "success": False,
                "message": f"Slot with QR code {slot_name} not found in any storage.",
            }
        )

    storage = slot.storage
    dispatcher = LED_shelf_dispatcher(storage)

    # Check if ANY slot in the combined group is occupied
    if is_combined_slot_occupied(slot):
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

        # Find which specific slot in the group is occupied for error message
        occupied_slot = None
        all_slot_names = slot.get_all_slot_names()
        related_slots = StorageSlot.objects.filter(
            storage=slot.storage, name__in=all_slot_names, carrier__isnull=False
        )
        if related_slots.exists():
            occupied_slot = related_slots.first()

        error_msg = f"Slot {slot_name} is part of a combined slot group where "
        if (
            occupied_slot
            and hasattr(occupied_slot, "carrier")
            and occupied_slot.carrier
        ):
            error_msg += (
                f"slot {occupied_slot.name} contains {occupied_slot.carrier.name}."
            )
        else:
            error_msg += "another slot is occupied."

        return JsonResponse(
            {
                "success": False,
                "message": error_msg,
            }
        )

    if slot.led_state == 0:
        return JsonResponse({"success": False, "message": "led is off but shouldn't"})

    carrier.storage_slot = slot
    carrier.save()
    StorageSlot.objects.filter(storage=storage).update(led_state=0)

    Thread(target=dispatcher.reset_leds).start()

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
            "message": f"Carrier {carrier.name} stored in storage {slot.storage.name} slot {slot_name}.",
        }
    )


@csrf_exempt
def get_free_slots(request, storage_name):
    """
    Get free slots for a specific storage
    """
    try:
        storage = Storage.objects.get(name=storage_name)
    except Storage.DoesNotExist:
        return JsonResponse({"error": "Storage not found"}, status=404)

    # Get all free slots in the storage
    free_slots = StorageSlot.objects.filter(
        storage=storage, carrier__isnull=True
    ).values("name", "qr_value", "diameter", "width")

    return JsonResponse({"storage": storage_name, "free_slots": list(free_slots)})


@csrf_exempt
def fetch_available_storages_for_auto(request):
    """
    Fetch all available storages for automatic operations
    """
    storages = Storage.objects.filter(archived=False).values("name")

    return JsonResponse({"available_storages": list(storages)})


@csrf_exempt
def store_carrier_choose_slot_all_storages(request, carrier_name):
    """
    Choose slot for carrier across all storages
    """
    carrier_name = carrier_name.strip()

    try:
        carrier = Carrier.objects.get(name=carrier_name, archived=False)
    except Carrier.DoesNotExist:
        return JsonResponse({"error": "Carrier not found"}, status=404)

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
        return JsonResponse(
            {"success": False, "message": "Carrier is in machine slot."}
        )

    # Find all storages with free slots that can accommodate this carrier
    available_storages = []
    
    # Create dispatchers for storages that have available slots
    dispatchers = {}
    all_free_slots = []

    for storage in Storage.objects.filter(archived=False):
        free_slots = get_truly_free_slots(storage, carrier.diameter, carrier.width)

        if free_slots:
            available_storages.append(
                {
                    "storage_name": storage.name,
                    "free_slot_count": len(free_slots),
                    "slots": [slot.qr_value for slot in free_slots],
                }
            )
            
            # Create dispatcher for this storage
            dispatchers[storage.name] = LED_shelf_dispatcher(storage)
            all_free_slots.extend(free_slots)

    if not available_storages:
        return JsonResponse(
            {
                "success": False,
                "message": "No available slots found in any storage for this carrier.",
            }
        )

    # MISSING LOGIC IMPLEMENTATION: Turn on the LEDs for all available slots
    
    # 1. Update LED state for all free slots in database
    all_free_slot_ids = [slot.id for slot in all_free_slots]
    StorageSlot.objects.filter(id__in=all_free_slot_ids).update(led_state=1)

    # 2. Light up LEDs for each storage that has available slots
    for storage in Storage.objects.filter(archived=False):
        free_slots_for_storage = get_truly_free_slots(storage, carrier.diameter, carrier.width)
        
        if free_slots_for_storage and storage.name in dispatchers:
            # Create lights_dict for this storage
            lights_dict = {"lamps": {}}
            
            for free_slot in free_slots_for_storage:
                # Add all related slot LEDs for combined slots
                all_names = free_slot.get_all_slot_names()
                for name in all_names:
                    lights_dict["lamps"][name] = "yellow"
            
            # Start thread to light up LEDs for this storage
            Thread(
                target=dispatchers[storage.name]._LED_On_Control,
                kwargs={"lights_dict": lights_dict},
            ).start()

    return JsonResponse(
        {
            "success": True,
            "carrier": carrier.name,
            "available_storages": available_storages,
        }
    )


def store_auto_with_storage_selection(request, carrier_id, storage_name):
    """
    Modified auto storage endpoint that requires storage selection first
    This would replace or supplement the existing auto storage endpoint
    URL pattern: store_auto_with_storage_selection/<int:carrier_id>/<storage_name>/
    """
    try:
        carrier_id = int(carrier_id)
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "message": "Invalid carrier ID."})

    storage_name = storage_name.strip()

    # Validate carrier (same as existing auto storage logic)
    try:
        carrier = Carrier.objects.get(name=carrier_id, archived=False)
    except Carrier.DoesNotExist:
        return JsonResponse({"success": False, "message": "Carrier not found."})

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
        return JsonResponse(
            {"success": False, "message": "Carrier is in machine slot."}
        )

    # Validate storage
    try:
        storage = Storage.objects.get(name=storage_name, archived=False)
    except Storage.DoesNotExist:
        return JsonResponse({"success": False, "message": "Storage not found."})

    # Continue with existing auto storage logic but for the selected storage
    # This calls the existing store_carrier function but with the selected storage
    return store_carrier(request, carrier.name, storage_name)


def store_carrier_choose_slot_cancel(request, carrier_name, storage_name):
    StorageSlot.objects.filter(storage=storage_name).update(led_state=0)
    storage = Storage.objects.filter(name=storage_name)
    storage.update(lighthouse_A_yellow=False, lighthouse_B_yellow=False)
    dispatcher = LED_shelf_dispatcher(storage.first())
    Thread(target=dispatcher.reset_leds, kwargs={"working_light": True}).start()

    return JsonResponse({"success": True})
