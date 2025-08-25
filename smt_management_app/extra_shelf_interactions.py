from threading import Thread

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

try:
    storages = Storage.objects.all()
    if storages:
        # initialize the dispatchers for all shelfs to turn on the working lights to green
        dispatchers = {
            storage.name: LED_shelf_dispatcher(storage) for storage in storages
        }
except Exception:
    pass


@csrf_exempt
def change_slot_color(request, storage_name, slot_name, color):
    """
    Changes the color of a slot in a storage unit.

    Args:
    - request: HTTP request object
    - storage_name: Name of the storage unit
    - slot_name: Name of the slot
    - color: Color to change the slot to

    Returns:
    - JsonResponse indicating success or failure
    """
    storage_name = storage_name.strip()
    slot_name = slot_name.strip()
    color = color.strip()

    slot_queryset = StorageSlot.objects.filter(
        storage__name=storage_name, name=slot_name
    )

    if not slot_queryset:
        return JsonResponse(
            {
                "success": False,
                "message": f"Could not find slot {slot_name} in storage {storage_name}.",
            }
        )

    if not color in ["red", "green", "yellow", "blue"]:
        return JsonResponse(
            {
                "success": False,
                "message": f"Invalid color {color}. Possible values are 'red', 'green', 'yellow', 'blue'.",
            }
        )

    slot = slot_queryset.first()
    slot.led_state = 1
    slot.save()

    led_dispatcher = LED_shelf_dispatcher(slot.storage)
    Thread(
        target=led_dispatcher.led_on,
        kwargs={"lamp": slot.name, "color": color},
    ).start()
    slot.led_state = 1
    slot.save()

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
        target=led_dispatcher._LED_On_Control,
        kwargs={"lights_dict": {"status": {"A": "green", "B": "green"}}},
    )
    # Update LED state for all storage slots to 0
    StorageSlot.objects.filter(storage=storage).update(led_state=0)

    # Return JSON response indicating LED reset for the given storage
    return JsonResponse({"reset_led": storage.name})
