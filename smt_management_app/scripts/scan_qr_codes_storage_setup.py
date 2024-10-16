from smt_management_app.models import Storage, StorageSlot
from smt_management_app.utils.led_shelf_dispatcher import LED_shelf_dispatcher


def run():
    #storages_queryset = Storage.objects.all()
    storages_queryset = Storage.objects.filter(name="Neolight Konferenzraum")
    for storage in storages_queryset:
        slot_queryset = StorageSlot.objects.filter(storage=storage)
        sorted_slot_queryset = sorted(slot_queryset, key=lambda slot: int(slot.name))
        led_dispatcher = LED_shelf_dispatcher(storage)
        led_dispatcher.reset_leds()
        for slot in sorted_slot_queryset:
#            if slot.name < 601 or slot.name > 700:#left top side is reverse (LED adresses are, qr are not) so we need to relabel
#                continue
            led_dispatcher.led_on(int(slot.name), "blue")
            qr_value = input(f"Please scan the barcode of the indicated slot.")
            led_dispatcher.led_off(int(slot.name))
            slot.qr_value = qr_value
            slot.save()
