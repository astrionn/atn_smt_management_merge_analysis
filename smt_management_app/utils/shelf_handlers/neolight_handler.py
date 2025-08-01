import requests
from urllib.parse import urlunsplit, urljoin
from pprint import pprint as pp
import time
import random

t = 0.25


class NeoLightAPI:
    def __init__(
        self,
        ip,
        port=5000,
        max_led_address=1400,
        led_colors=["red", "green", "yellow", "blue"],
        tower_colors=["green", "yellow", "red"],
    ):
        self.__api_url = urlunsplit(["http", f"{ip}:{port}", "/", None, None])
        self.led_colors = led_colors
        self.tower_colors = tower_colors
        self.all_leds = list(range(1, max_led_address + 1))

    def _LED_On_Control(self, lights_dict):
        """
        lights_dict = {'status':{'A':'green','B':'yellow'}, 'lamps'={1:'red',2:'yellow',3:'green',4:'blue'}}
        lights_dict = {'status':{'A':'green'}}
        lights_dict = {'lamps'={1:'red',2:'yellow',3:'green',4:'blue'}}
        """
        print(f"LIGHTS DICT {lights_dict}")
        param_list = []
        for k in lights_dict.keys():
            if k == "status":
                if not lights_dict[k]:
                    raise Exception(f"no valid value for key {k}")
                for stat in lights_dict[k].keys():
                    if stat not in ["A", "B"]:
                        raise Exception(f"no valid value for key {stat} for key {k}")
                    if lights_dict[k][stat] not in self.tower_colors:
                        raise Exception(
                            f"bad color {lights_dict[k][stat]} for status light. possible values are {self.tower_colors}"
                        )
                    param_list.append(f"status{stat}={lights_dict[k][stat]}")

            elif k == "lamps":
                if not lights_dict[k]:
                    raise Exception(f"no valid value for key {k}")
                for l in lights_dict[k].keys():
                    if not str(l).isdigit() or str(l) == "0":
                        #raise Exception(f"bad value {l} as lamp address")
                        print(f"bad value {l} as lamp address")
                    if not lights_dict[k][l] in self.led_colors:
                        raise Exception(
                            f"bad color {lights_dict[k][l]} for led light. possible values are {self.led_colors}"
                        )
                    # 1   => 001-01-001
                    # 2   => 001-01-002
                    # 101 => 001-02-001
                    # 201 => 001-03-001
                    # 701
                    # seite-reihe-fach
                    slotid = l
                    param_list.append(f"{slotid}={lights_dict[k][l]}")
            else:
                raise Exception(f"key: {k} not expected")

        param_string = ";".join(param_list)
        # print(f'PARAM STR : {param_string}')
        request_param_dict = {"params": param_string}

        req = requests.post(
            urljoin(self.__api_url, "/api/open"), json=request_param_dict
        )
        print(f"LEDCTRL:::{req.url}\n{req.request.body}\n{req}\n{req.content}")
        return req

    def _LED_Off_Control(self, lamps=[], statusA=False, statusB=False):
        if lamps:
            request_param_dict = {
                "params": ";".join([l.__str__() for l in lamps])
                + (";statusA" if statusA else "")
                + (";statusB" if statusB else "")
            }
        else:
            request_param_dict = {
                "params": ""
                + ("statusA" if statusA else "")
                + (";" if statusA and statusB else "")
                + ("statusB" if statusB else "")
            }
        req = requests.post(
            urljoin(self.__api_url, "api/close"), json=request_param_dict
        )
        return req

    def _LED_On_and_Off_Control(self, state="off"):
        request_param_dict = {"op": f"{state}"}
        req = requests.post(urljoin(self.__api_url, "/opAll"), json=request_param_dict)
        return req

    def led_on(self, lamp, color):
        # print(f"in led_on lamp={lamp},color={color}")
        # lamp = self.side_row_lamp_to_led_address(lamp)
        if color not in self.led_colors:
            raise ValueError(
                f"Invalid color {color} for LED. Possible values are {self.led_colors}"
            )

        lights_dict = {"lamps": {int(lamp): color}}
        # print(f"in led_on passing lights dict: {lights_dict}")
        return self._LED_On_Control(lights_dict)

    def led_off(self, lamp):
        # lamp = self.side_row_lamp_to_led_address(lamp)
        return self._LED_Off_Control([str(lamp)])

    def reset_leds(self, working_light=False, all_leds=[]):
        if not all_leds:
            all_leds = self.all_leds
        if working_light:
            r = self._LED_Off_Control(all_leds, True, True)
        else:
            r = self._LED_Off_Control(all_leds, False, False)
        return r

    def test(self, stop=200):
        IT = self
        for i in range(stop + 1):
            on_lamps = {
                "status": {
                    random.choice(["A", "B"]): random.choice(["red", "green", "yellow"])
                },
                "lamps": {
                    k: random.choice(["red", "green", "yellow", "blue"])
                    for k in range(1, 1400)
                },
            }
            time.sleep(t)
            IT._LED_On_Control(on_lamps)
            num_integers = random.randint(1, 1400)
            random_integers = []
            for i in range(num_integers):
                random_integers.append(random.randint(1, 1400))
            time.sleep(t)
            IT._LED_Off_Control(random_integers)

    def test1(self, stop=100):
        for i in range(stop):
            for j in range(1, 8):
                color = random.choice(["red", "green", "yellow", "blue"])
                self._LED_On_Control(
                    {"lamps": {l: color for l in range((j - 1) * 100 + 1, j * 100 + 1)}}
                )
                if j != 1:
                    self._LED_On_Control(
                        {
                            "lamps": {
                                l: color
                                for l in range(
                                    ((j - 1) * 100 + 1) + 600, (j * 100 + 1) + 600
                                )
                            }
                        }
                    )
                time.sleep(t)
                if j > 2:
                    self._LED_Off_Control(
                        [k for k in range((j - 3) * 100 + 1, (j - 2) * 100 + 1)]
                    )

            self.reset_leds()
            if i % 2 == 0:
                self.test(2)
            else:
                self.test2(1)
            self.reset_leds()

    def test2(self, stop=1):
        for i in range(stop):
            for color in ["red", "green", "yellow", "blue"]:
                self._LED_On_Control({"lamps": {j: color for j in range(1, 1401)}})
                time.sleep(t * 3)
                self.reset_leds()
