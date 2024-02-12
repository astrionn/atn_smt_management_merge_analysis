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
        taraget=led_dispatcher._LED_On_Control,
        kwargs={"lights_dict": {"status": {"A": "green", "B": "green"}}},
    )
    # Update LED state for all storage slots to 0
    StorageSlot.objects.filter(storage=storage).update(led_state=0)

    # Return JSON response indicating LED reset for the given storage
    return JsonResponse({"reset_led": storage})
