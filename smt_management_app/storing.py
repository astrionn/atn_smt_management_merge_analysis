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


def store_carrier_choose_slot_cancel(request, carrier_name, storage_name):
    StorageSlot.objects.filter(storage=storage_name).update(led_state=0)
    storage = Storage.objects.filter(name=storage_name)
    storage.update(lighthouse_A_yellow=False, lighthouse_B_yellow=False)
    dispatcher = LED_shelf_dispatcher(storage.first())
    Thread(target=dispatcher.reset_leds, kwargs={"working_light": True}).start()

    return JsonResponse({"success": True})
