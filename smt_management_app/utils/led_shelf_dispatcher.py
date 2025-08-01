from gc import enable
import re
import time
from pprint import pprint as pp
from ..models import StorageSlot, Storage
from .shelf_handlers.neolight_handler import NeoLightAPI
from .shelf_handlers.PTL_handler import PTL_API
from .shelf_handlers.xgate_handler import XGateHandler


class LED_shelf_dispatcher:

    def __init__(self, storage):
        self.storage = storage
        self.device_type = storage.device
        self.ip_address = None
        self.ip_port = None
        self.COM_address = None
        self.COM_baudrate = None
        self.COM_timeout = None
        self.ATNPTL_shelf_id = None
        self.device_handler = None

        match self.device_type:
            case "ATNPTL":
                # ATNPTL has no workinglight/lighthouse
                # ATNPTL has no interface to switch multiple lights at once
                self.COM_address = storage.COM_address
                self.ATNPTL_shelf_id = storage.ATNPTL_shelf_id
                self.COM_baudrate = storage.COM_baudrate
                self.COM_timeout = storage.COM_timeout
                self.device_handler = PTL_API(
                    port=self.COM_address,
                    baudrate=self.COM_baudrate,
                    timeout=self.COM_timeout,
                )
            case "NeoLight":
                # NeoLight has workinglights
                # NeoLight has an interface to switch multiple lights at once
                self.ip_address = storage.ip_address
                self.ip_port = storage.ip_port
                self.device_handler = NeoLightAPI(
                    ip=self.ip_address, port=self.ip_port
                )  # 192.168.178.11 weytronik

                self.enable_working_lights_based_on_led_state()
            case "Sophia":
                # Sophia has one workinglight
                # Sophia PROBABLY has no interface to switch multiple lights at once, recheck docs
                # for now we treat Sophia as single command switch
                self.ip_address = storage.ip_address
                self.device_handler = XGateHandler(
                    xgate_address=self.ip_address
                )  # 192.168.0.10 siemens AT
                self._LED_On_Control(
                    lights_dict={"status": {"A": "green", "B": "green"}}
                )
            case "Dummy":
                self.enable_working_lights_based_on_led_state()

    def enable_working_lights_based_on_led_state(self):
        enabled_leds = StorageSlot.objects.filter(storage=self.storage, led_state=1)

        if enabled_leds:

            if (
                all(led.name <= (self.storage.capacity // 2) for led in enabled_leds)
                and self.storage.lighthouse_B_yellow
            ):
                self.storage.lighthouse_B_yellow = False
                self.storage.save()
                self.lighthouse_off_control(statusB=True)
            if (
                all(led.name > (self.storage.capacity // 2) for led in enabled_leds)
                and self.storage.lighthouse_A_yellow
            ):
                self.storage.lighthouse_A_yellow = False
                self.storage.save()
                self.lighthouse_off_control(statusA=True)

            if (
                any(led.name <= (self.storage.capacity // 2) for led in enabled_leds)
                and not self.storage.lighthouse_A_yellow
            ):
                self.storage.lighthouse_A_yellow = True
                self.storage.save()
                self.lighthouse_on_control(lights_dict={"status": {"A": "yellow"}})
            if (
                any(led.name > (self.storage.capacity // 2) for led in enabled_leds)
                and not self.storage.lighthouse_B_yellow
            ):
                self.storage.lighthouse_B_yellow = True
                self.storage.save()
                self.lighthouse_on_control(lights_dict={"status": {"B": "yellow"}})

        else:
            self.lighthouse_off_control()
            self.storage.lighthouse_A_green = False
            self.storage.lighthouse_B_green = False
            self.storage.lighthouse_A_yellow = False
            self.storage.lighthouse_B_yellow = False
            self.storage.save()
        if not (self.storage.lighthouse_A_green and self.storage.lighthouse_B_green):
            self.lighthouse_on_control()
            self.storage.lighthouse_A_green = True
            self.storage.lighthouse_B_green = True
            self.storage.save()

    def lighthouse_on_control(
        self, lights_dict={"status": {"A": "green", "B": "green"}}
    ):
        match self.device_type:
            case "ATNPTL":
                print("ATNPTL has no lighthouse")
            case "NeoLight":
                self.device_handler._LED_On_Control(lights_dict=lights_dict)
            case "Sophia":
                workinglight_dictionary = lights_dict.get("status", None)
                lamps_dictionary = lights_dict.get("lamps", None)
                if workinglight_dictionary:
                    self.device_handler.light_house_on(mode="normal")
                if lamps_dictionary:
                    for lamp, color in lamps_dictionary.items():
                        self.led_on(lamp=lamp, color=color)
            case "Dummy":
                print(f"LIGHTHOUSE ON {self.storage.name}")
                pp(lights_dict)

    def lighthouse_off_control(self, statusA=True, statusB=True):
        match self.device_type:
            case "ATNPTL":
                print("ATNPTL has no lighthouse")
            case "NeoLight":
                self.device_handler._LED_Off_Control(statusA=statusA, statusB=statusB)
            case "Sophia":
                pass
            case "Dummy":
                print(f"LIGHTHOUSE LED OFF {self.storage.name} {statusA=} {statusB=}")

    def test_leds(self):
        """
        Test all LEDs by cycling through all colors for all slots 5 times.
        Each hardware type is handled according to its specific requirements.
        """
        # Get all slots for this storage from the database
        all_slots = StorageSlot.objects.filter(storage=self.storage)

        # Define colors to cycle through
        colors = ["red", "green", "yellow"]

        # Cycle 5 times
        match self.device_type:
            case "ATNPTL":
                # Reset all LEDs before starting
                self.device_handler.reset_leds(shelf=self.ATNPTL_shelf_id)

                for cycle in range(5):
                    for color in colors:
                        # Turn on all slots with current color
                        for slot in all_slots:
                            time.sleep(1)
                            self.device_handler.led_on(
                                shelf=self.ATNPTL_shelf_id, lamp=slot.name, color=color
                            )

                        # Wait a bit to make the effect visible
                        import time

                        time.sleep(1)

                        # Turn off all slots
                        for slot in all_slots:
                            self.device_handler.led_off(
                                slot.name, shelf=self.ATNPTL_shelf_id
                            )

                # Reset all LEDs after testing
                self.device_handler.reset_leds(shelf=self.ATNPTL_shelf_id)

            case "NeoLight":
                # Reset all LEDs before starting
                self.device_handler.reset_leds(working_light=True)

                for cycle in range(5):
                    for color in colors:
                        # Turn on all slots with current color
                        for slot in all_slots:
                            self.device_handler.led_on(slot.name, color)

                        # Wait a bit to make the effect visible
                        import time

                        time.sleep(1)

                        # Turn off all slots
                        for slot in all_slots:
                            self.device_handler.led_off(slot.name)

                # Reset all LEDs after testing
                self.device_handler.reset_leds(working_light=True)
                self.enable_working_lights_based_on_led_state()

            case "Sophia":
                # Reset all LEDs before starting
                self.device_handler.clear_leds()
                self.device_handler.clear_lhs()

                for cycle in range(5):
                    for color in colors:
                        # Turn on all slots with current color
                        for slot in all_slots:
                            row, led = self._xgate_slot_to_row_led(slot.name)
                            self.device_handler.switch_lights(
                                address=row, lamp=led, col=color, blink=False
                            )

                        # Wait a bit to make the effect visible
                        import time

                        time.sleep(1)

                        # Turn off all slots (using "off" color)
                        for slot in all_slots:
                            row, led = self._xgate_slot_to_row_led(slot.name)
                            self.device_handler.switch_lights(
                                address=row, lamp=led, col="off", blink=False
                            )

                # Reset all LEDs after testing
                self.device_handler.clear_leds()
                self.device_handler.clear_lhs()
                self._LED_On_Control(
                    lights_dict={"status": {"A": "green", "B": "green"}}
                )

            case "Dummy":
                print(f"Testing LEDs for {self.storage.name}")
                print(f"Found {len(all_slots)} slots to test")
                print(f"Colors to test: {colors}")

                for cycle in range(5):
                    print(f"Starting test cycle {cycle + 1}/5")

                    for color in colors:
                        print(f"Testing color: {color}")

                        # Turn on all slots with current color
                        for slot in all_slots:
                            print(f"led on {self.storage.name} {slot.name=} ; {color=}")

                        # Wait a bit to make the effect visible
                        import time

                        time.sleep(1)

                        # Turn off all slots
                        for slot in all_slots:
                            print(f"led off {self.storage.name} {slot.name=}")

                    print(f"Completed test cycle {cycle + 1}/5")

                print("LED testing completed")
                self.enable_working_lights_based_on_led_state()

    def led_on(self, lamp, color):
        match self.device_type:
            case "ATNPTL":
                print(
                    f"led on {self.storage.name} with ID {self.ATNPTL_shelf_id} {lamp=} ; {color=}"
                )
                self.device_handler.led_on(
                    lamp=lamp, color=color, shelf=self.ATNPTL_shelf_id
                )
                self.device_handler.led_on(
                    lamp=lamp, color=color, shelf=self.ATNPTL_shelf_id
                )
            case "NeoLight":
                self.device_handler.led_on(lamp, color)
                self.enable_working_lights_based_on_led_state()
            case "Sophia":
                row, led = self._xgate_slot_to_row_led(lamp)
                self.device_handler.switch_lights(
                    address=row, lamp=led, col=color, blink=False
                )
            case "Dummy":
                print(f"led on {self.storage.name} {lamp=} ; {color=}")
                self.enable_working_lights_based_on_led_state()

    def led_off(self, lamp):
        match self.device_type:
            case "ATNPTL":
                self.device_handler.led_off(lamp=lamp, shelf=self.ATNPTL_shelf_id)
            case "NeoLight":
                self.device_handler.led_off(lamp)
                self.enable_working_lights_based_on_led_state()
            case "Sophia":
                self.led_on(lamp, "off")
            case "Dummy":
                print(f"led off {self.storage.name} {lamp=}")
                self.enable_working_lights_based_on_led_state()

    def _LED_On_Control(self, lights_dict):
        match self.device_type:
            case "ATNPTL":
                for lamp, color in lights_dict["lamps"].items():
                    self.led_on(lamp=lamp, color=color)
            case "NeoLight":
                self.device_handler._LED_On_Control(lights_dict=lights_dict)
                self.enable_working_lights_based_on_led_state()
            case "Sophia":
                workinglight_dictionary = lights_dict.get("status", None)
                lamps_dictionary = lights_dict.get("lamps", None)
                if workinglight_dictionary:
                    self.device_handler.light_house_on(mode="normal")
                if lamps_dictionary:
                    for lamp, color in lamps_dictionary.items():
                        self.led_on(lamp=lamp, color=color)
            case "Dummy":
                print(f"LED ON {self.storage.name}")
                pp(lights_dict)
                self.enable_working_lights_based_on_led_state()

    def _LED_Off_Control(self, lamps=[], statusA=False, statusB=False):
        match self.device_type:
            case "ATNPTL":
                for lamp in lamps:
                    self.led_off(lamp=lamp)
            case "NeoLight":
                self.device_handler._LED_Off_Control(
                    lamps=lamps, statusA=statusA, statusB=statusB
                )
                self.enable_working_lights_based_on_led_state()
            case "Sophia":
                for lamp in lamps:
                    self.led_off(lamp)
                if statusA or statusB:
                    self.device_handler.clear_lhs()
            case "Dummy":
                print(f"Led OFF {self.storage.name} {statusA=} {statusB=}")
                pp(lamps)
                self.enable_working_lights_based_on_led_state()

    def reset_leds(self, working_light=False):
        print(f"HANDLER CONFIRM CHOOSE SLOT START")
        match self.device_type:
            case "ATNPTL":
                self.device_handler.reset_leds(controller=self.ATNPTL_shelf_id)
            case "NeoLight":
                # pass all slot names instae dof hardcoded mapping, to avoid discrepancies bettween 0 indexed and 1 indexed leds
                all_leds = StorageSlot.objects.filter(storage=self.storage).values_list("name", flat=True)
                self.device_handler.reset_leds(working_light=working_light,all_leds=all_leds)
                if working_light:
                    self.storage.lighthouse_A_yellow = False
                    self.storage.lighthouse_B_yellow = False
                    self.storage.save()
                self.lighthouse_on_control()
                print(f"HANDLER CONFIRM CHOOSE SLOT END")
            case "Sophia":
                self.device_handler.clear_leds()
                if working_light:
                    self.device_handler.clear_lhs()
            case "Dummy":
                print(f"reset leds {self.storage.name}")
                if working_light:
                    print(f"reset workinglight {self.storage.name}")
                    self.storage.lighthouse_A_yellow = False
                    self.storage.lighthouse_B_yellow = False
                    self.storage.save()
                self.lighthouse_on_control()

    def _xgate_slot_to_row_led(self, lamp):
        # the barcodes on the storage slots have a 5 char long prefix and the slot id is formatted a little differntly then its printed under the barcode
        # barcode value: L1607A1001
        # text beneath: A1-001
        # xgate call signature for this slot: row 1 lamp 1
        # there is 7 rows per side of the shelf, then it wraps to the 2nd side
        # barcode value: L1607B1001
        # text beneath: B1-001
        # xgate call signature for this slot: row 11 lamp 1
        row_part, led_part = lamp.split("-")
        return int(re.sub("B", "1", re.sub("A", "", row_part))), int(led_part)
