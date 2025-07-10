# Modified PTL_handler.py
import time
import requests


class PTL_API:
    def __init__(
        self,
        port,
        baudrate=115200,
        timeout=0.4,
        connection=None,
        flask_url="http://127.0.0.1:5000",
    ):
        print("PTL_API arg", port)
        self.port = str(port)
        print("PTL_API val", self.port)
        self.baudrate = baudrate
        self.flask_url = flask_url
        self.connected = False
        self.timeout = timeout

        # Initialize connection to Flask service
        if not connection:  # If no connection is provided, use Flask service
            max_attempts = 5
            attempts = 0
            while not self.connected and attempts < max_attempts:
                attempts += 1
                try:
                    response = requests.post(
                        f"{self.flask_url}/initialize",
                        json={
                            "port": self.port,
                            "baudrate": self.baudrate,
                            "timeout": self.timeout,
                        },
                    )

                    if response.status_code == 200 and response.json()["success"]:
                        self.connected = True
                        print(
                            f"Connected to Flask service: {response.json()['message']}"
                        )
                    else:
                        print(
                            f"Failed to connect: {response.json().get('message', 'Unknown error')}"
                        )
                        time.sleep(1)  # Wait before retry
                except requests.RequestException as e:
                    print(f"Error connecting to Flask service: {str(e)}")
                    time.sleep(1)

                if attempts >= max_attempts:
                    print(
                        f"Failed to establish connection after {max_attempts} attempts"
                    )
                    break
        else:
            # If connection is provided (for testing or special cases),
            # we're setting connected to True but not actually using the connection
            self.connected = True
            print("Using provided connection (this is ignored in HTTP mode)")

        # Slot to strip mapping remains unchanged
        self.slot_to_strip_map = {
            1: 1,
            2: 3,
            3: 6,
            4: 9,
            5: 12,
            6: 15,
            7: 18,
            8: 20,
            9: 23,
            10: 26,
            11: 29,
            12: 32,
            13: 35,
            14: 38,
            15: 41,
            16: 44,
            17: 47,
            18: 49,
            19: 52,
            20: 55,
            21: 58,
            22: 61,
            23: 64,
            24: 66,
            25: 69,
            26: 72,
            27: 75,
            28: 78,
            29: 81,
            30: 84,
            31: 87,
            32: 90,
            33: 93,
            34: 96,
            35: 98,
            36: 101,
            37: 104,
            38: 107,
            39: 110,
            40: 113,
            41: 116,
            42: 118,
            43: 121,
            44: 124,
            45: 127,
            46: 130,
            47: 133,
            48: 136,
            49: 138,
            50: 140,
        }

    def _LED_strip_control(
        self,
        gateway=1,
        controller=1,
        command=11,
        channel=0,
        led_C=0,
        led_D=0,
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
        print(
            [
                "STX",
                "GATEWAY",
                "CONTROLLER",
                "COMMAND",
                "CHANNEL",
                "led_C",
                "led_D",
                "R",
                "G",
                "B",
                "BLINK",
                "RESERVED",
            ]
        )

        # Send command to Flask service instead of directly to serial port
        try:
            response = requests.post(
                f"{self.flask_url}/send_command",
                json={"command": cmd, "read_size": 5},
                timeout=2,
            )

            if response.status_code == 200 and response.json()["success"]:
                print("written bytes no: ", response.json()["written_bytes"])
                print("res", response.json()["response"])
                return response.json()["response"]
            else:
                error_msg = response.json().get("message", "Unknown error")
                print(f"Command failed: {error_msg}")
                # Try to reconnect if connection issue
                if "connection" in error_msg.lower():
                    self.connected = False
                return None
        except requests.RequestException as e:
            print(f"Error sending command to Flask service: {str(e)}")
            self.connected = False
            return None

    # The rest of the methods remain unchanged as they call _LED_strip_control
    def LED_slot_control(
        self, gateway=1, controller=1, command=11, channel=1, LED=1, R=0, G=0, B=0
    ):
        print(
            f"LED_slot_control {gateway=} {controller=} {command=} {channel=} {LED=} {R=} {G=} {B=}"
        )
        if LED > len(self.slot_to_strip_map):
            raise Exception(
                f"Value {LED} for slot ID is out of range {len(self.slot_to_strip_map)}"
            )

        led = self.slot_to_strip_map[LED]
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
        print(
            f"LED_slot_code_control {gateway=} {controller=} {command=} {code=} {R=} {G=} {B=}"
        )
        row = int(str(code).zfill(4)[0])  # thousand bit (1234 -> 1)
        led = int(str(code).zfill(4)[1:])  # other bits (1234 -> 234)
        print(f"channel: {row=}, {led=}")
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

    def led_on(self, shelf=None, lamp=1, color="blue"):
        print(f"LED ON {shelf=} {lamp=} {color=}")
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

    def led_off(self, shelf=1, lamp=1001):
        self.LED_slot_code_control(gateway=1, controller=shelf, command=21, code=lamp)

    def reset_leds(self, working_light=None, controller=1):
        self._LED_strip_control(command=23, controller=controller)

    # Test methods remain unchanged
    def test_lower_layer(self, inf=False):
        ceil = 2
        k = 1
        if inf:
            ceil = 100
        while k < ceil:
            vals = list(range(1, 150))
            for j, i in enumerate(vals):
                r = 255 if j % 3 == 2 else 0
                g = 255 if j % 3 == 1 else 0
                b = 255 if j % 3 == 0 else 0
                c = str(i).zfill(3)[0]
                d = str(i).zfill(3)[1:]
                self._LED_strip_control(
                    led_C=int(c), led_D=int(d), R=r, G=g, B=b, channel=(k % 4 + 1)
                )
            if k % 4 == 0:
                self.reset_leds()
            k += 1

    def test_higher_layer(self, step=False, inf=False):
        ceil = 2
        j = 1
        if inf:
            ceil = 100
        while j < ceil:
            for i in (
                []
                + list(range(1001, 1051))
                + list(range(2002, 2051))
                + list(range(3002, 3051))
                + list(range(4002, 4051))
            ):
                c = ["red", "green", "blue", "yellow"][i % 4]
                self.led_on(lamp=i, color=c, shelf=1)
                if step:
                    input(f"{i=}, {c=}")
            j += 1
            self.reset_leds()

    def test(self, step=False, inf=False):
        ceil = 2
        j = 1
        if inf:
            ceil = 100
        while j < ceil:
            for i in (
                []
                + list(range(1001, 1051))
                + list(range(2002, 2051))
                + list(range(3002, 3051))
                + list(range(4002, 4051))
                + list(range(5002, 5051))
                + list(range(6002, 6051))
                + list(range(7002, 7051))
                + list(range(8002, 8051))
            ):
                c = ["red", "green", "blue", "yellow"][i % 4]
                self.led_on(lamp=i, color=c, shelf=1)
                if step:
                    input(f"{i=}, {c=}")

            j += 1
            # self.reset_leds()
