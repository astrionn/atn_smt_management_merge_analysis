import time
from smt_management_app.models import Storage, StorageSlot
from smt_management_app.utils.led_shelf_dispatcher import LED_shelf_dispatcher


def run():
    storages = Storage.objects.all()
    for storage in storages:
        led_dispatcher = LED_shelf_dispatcher(storage)
        led_dispatcher.reset_leds()
        slots = StorageSlot.objects.filter(storage=storage)
        slots = sorted(slots, key=lambda ss: int(ss.name))
        for slot in slots:
            led_dispatcher.led_on(slot.name, "green")
            time.sleep(0.2)
        led_dispatcher.reset_leds()
