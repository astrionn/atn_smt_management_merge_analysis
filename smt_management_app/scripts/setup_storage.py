from smt_management_app.models import StorageSlot
from smt_management_app.utils.neolight_handler import NeoLightAPI


def run():
    class NeoDummy:
        # for developement without actually having to connect a shelf
        def __init__(self):
            pass

        def led_on(self, lamp, color):
            print(f"led on {lamp=} ; {color=}")

        def led_off(self, lamp):
            print(f"led of {lamp=}")

        def reset_leds(self, working_light=False):
            print("reset leds")

    # neo = NeoLightAPI("192.168.178.11")
    neo = NeoDummy()
    neo.reset_leds()
    qs = StorageSlot.objects.all()
    qs = sorted(qs, key=lambda ss: int(ss.name))

    for ss in qs:
        neo.led_on(int(ss.name), "blue")
        qr_value = input(f"Please scan the barcode of the indicated slot.")
        neo.led_off(int(ss.name))
        ss.qr_value = qr_value
        ss.save()
