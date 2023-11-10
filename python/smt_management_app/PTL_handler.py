import random
from pprint import pprint as pp
import serial
import serial.tools.list_ports as list_ports_


class PTL_API:
    def __init__(self, port):
        self.port = port
        self.baudrate = 9600
        self.serial = serial.Serial(
            port=self.port, baudrate=self.baudrate, timeout=0.25
        )
        self.slot_to_strip_map = {
            k: v + 1
            for k, v in enumerate(
                [
                    1,
                    2,
                    5,
                    8,
                    11,
                    14,
                    17,
                    20,
                    23,
                    26,
                    29,
                    32,
                    35,
                    38,
                    41,
                    42,
                    45,
                    48,
                    51,
                    54,
                    57,
                    60,
                    63,
                    66,
                    69,
                    71,
                    73,
                    76,
                    79,
                    82,
                    85,
                    88,
                    91,
                    94,
                    97,
                    99,
                    102,
                    105,
                    108,
                    111,
                    114,
                    117,
                    120,
                    123,
                    126,
                    129,
                    132,
                    135,
                    138,
                    140,
                ]
            )
        }

    def _LED_strip_control(
        self,
        gateway=1,
        controller=1,
        command=11,
        channel=1,
        led_C=0,
        led_D=1,
        R=0,
        G=0,
        B=0,
    ):
        cmd = [
            2,  # STX
            gateway,  # host
            controller,  # shelf
            command,  # 11 LED on, 21 LED Off, 22 Channel Off, 23 all off
            channel,  # row
            led_C,
            led_D,
            R,
            G,
            B,
            0,  # blink
            0,  # reserved
        ]
        print("channel: ", channel)
        print("lamp", led_C, led_D)
        print("cmd: ", cmd)
        byte_cmd = bytes(cmd)
        print("bytes: ", byte_cmd)
        query = self.serial.write(byte_cmd)
        print("written bytes no: ", query)
        res = self.serial.read(8)
        print("res", res)

    def LED_slot_control(
        self, gateway=1, controller=1, command=11, channel=1, LED=1, R=0, G=0, B=0
    ):
        if LED > len(self.slot_to_strip_map):
            raise Exception(
                f"Value {LED} for slot ID is out of range {len(self.slot_to_strip_map)}"
            )
        led = self.slot_to_strip_map[LED - 1]
        led_c = int(str(led).zfill(3)[0])  # hundred bit (123 -> 1)
        led_d = int(str(led).zfill(3)[1:])  # decimal bit (123 -> 23)

        self._LED_strip_control(
            gateway=gateway,
            controller=controller,
            command=command,
            channel=channel,
            led_C=led_c,
            led_D=led_d,
            R=R,
            G=G,
            B=B,
        )

    def LED_slot_code_control(
        self, gateway=1, controller=1, command=11, code=1001, R=0, G=0, B=0
    ):
        row = int(str(code).zfill(4)[0])  # thousand bit (1234 -> 1)
        led = int(str(code).zfill(4)[1:])  # other bits (1234 -> 234)

        self.LED_slot_control(
            gateway=gateway,
            controller=controller,
            command=command,
            channel=row,
            LED=int(led),
            R=R,
            G=G,
            B=B,
        )

    def led_on(self, shelf=1, lamp=1001, color="blue"):
        R = G = B = 0
        if color == "red":
            R = 255
        if color == "green":
            G = 255
        if color == "blue":
            B = 255
        if color == "yellow":
            R = 255
            G = 255

        self.LED_slot_code_control(
            gateway=1, controller=shelf, command=11, code=lamp, R=R, G=G, B=B
        )

    def led_off(self, shelf, lamp):
        self.LED_slot_code_control(gateway=1, controller=shelf, command=21, code=lamp)

    def reset_leds(self):
        self._LED_strip_control(command=23)


pp([p.__str__() for p in list_ports_.comports()])
ptl = PTL_API("COM16")
ptl.reset_leds()


def test_lower_layer():
    vals = list(range(1, 140))
    for j, i in enumerate(vals):
        r = 255 if j % 3 == 2 else 0
        g = 255 if j % 3 == 1 else 0
        b = 255 if j % 3 == 0 else 0
        c = str(i).zfill(3)[0]
        d = str(i).zfill(3)[1:]
        ptl._LED_strip_control(led_C=int(c), led_D=int(d), R=r, G=g, B=b)
    ptl.reset_leds()


def test_higher_layer():
    for i in (
        []
        + list(range(1001, 1051))
        + list(range(2002, 2051))
        + list(range(3002, 3051))
        + list(range(4002, 4051))
    ):
        c = ["red", "green", "blue", "yellow"][i % 4]
        ptl.led_on(lamp=i, color=c)
        print()
    ptl.reset_leds()


# test_higher_layer()
