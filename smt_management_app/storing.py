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
        target=LED_shelf_dispatcher(storage)._LED_On_Control,
        kwargs={
            "lights_dict": {
                "lamps": {
                    free_slot.name: "yellow"
                    for free_slot in free_slot_queryset.filter(storage=storage)
                }
            }
        },
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
                "message": f"Slot {slot_name} should contain {slot.carrier.name}.",
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
