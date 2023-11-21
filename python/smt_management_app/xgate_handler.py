import clr
import time

clr.AddReference(r"Ptl.Device")
clr.AddReference(r"System.Collections")
clr.AddReference(r"System")

from Ptl.Device import XGate, PtlIBS, PtlTera, Communication
from Ptl.Device.Communication.Command import LightMode
from Ptl.Device.Communication.Command import LightColor

from System import Byte, Int32
from System.Collections.Generic import *

import datetime

# CONSTANTS

LIGHT_OFF = Communication.Command.LightColor.Off
BLUE = Communication.Command.LightColor.Blue
GREEN = Communication.Command.LightColor.Green
RED = Communication.Command.LightColor.Red
YELLOW = Communication.Command.LightColor.Yellow
MAGNETA = Communication.Command.LightColor.Magenta
CYAN = Communication.Command.LightColor.Cyan
WHITE = Communication.Command.LightColor.White

COLORS = {
    "off": LIGHT_OFF,
    "blue": BLUE,
    "red": RED,
    "green": GREEN,
    "yellow": YELLOW,
    "magenta": MAGNETA,
    "cyan": CYAN,
    "white": WHITE,
}

LIGHTONOFFPERIOD100 = Communication.Command.LightOnOffPeriod.Period100
LIGHTONOFFPERIOD200 = Communication.Command.LightOnOffPeriod.Period200
LIGHTONOFFPERIOD500 = Communication.Command.LightOnOffPeriod.Period500
LIGHTONOFFPERIOD1000 = Communication.Command.LightOnOffPeriod.Period1000

BLINK_PERIODS = {
    "100": LIGHTONOFFPERIOD100,
    "200": LIGHTONOFFPERIOD200,
    "500": LIGHTONOFFPERIOD500,
    "1000": LIGHTONOFFPERIOD1000,
}

LIGHTONOFFRATIOP1V0 = Communication.Command.LightOnOffRatio.RatioP1V0
LIGHTONOFFRATIOP1V1 = Communication.Command.LightOnOffRatio.RatioP1V1
LIGHTONOFFRATIOP1V2 = Communication.Command.LightOnOffRatio.RatioP1V2
LIGHTONOFFRATIOP1V5 = Communication.Command.LightOnOffRatio.RatioP1V5
LIGHTONOFFRATIOP1V10 = Communication.Command.LightOnOffRatio.RatioP1V10
LIGHTONOFFRATIOP2V1 = Communication.Command.LightOnOffRatio.RatioP2V1
LIGHTONOFFRATIOP5V1 = Communication.Command.LightOnOffRatio.RatioP5V1
LIGHTONOFFRATIOP10V1 = Communication.Command.LightOnOffRatio.RatioP10V1

BLINK_RATIOS = {
    "p1v0": LIGHTONOFFRATIOP1V0,
    "p1v1": LIGHTONOFFRATIOP1V1,
    "p1v2": LIGHTONOFFRATIOP1V2,
    "p1v5": LIGHTONOFFRATIOP1V5,
    "p1v10": LIGHTONOFFRATIOP1V10,
    "p2v1": LIGHTONOFFRATIOP2V1,
    "p5v1": LIGHTONOFFRATIOP5V1,
    "p10v1": LIGHTONOFFRATIOP10V1,
}


BLINK_GREEN = LightMode()
BLINK_GREEN.Color = GREEN
BLINK_GREEN.Period = LIGHTONOFFPERIOD100
BLINK_GREEN.Ratio = LIGHTONOFFRATIOP1V1

BLINK_BLUE = LightMode()
BLINK_BLUE.Color = BLUE
BLINK_BLUE.Period = LIGHTONOFFPERIOD100
BLINK_BLUE.Ratio = LIGHTONOFFRATIOP1V1

BLINK_RED = LightMode()
BLINK_RED.Color = RED
BLINK_RED.Period = LIGHTONOFFPERIOD100
BLINK_RED.Ratio = LIGHTONOFFRATIOP1V1

BLINK_YELLOW = LightMode()
BLINK_YELLOW.Color = YELLOW
BLINK_YELLOW.Period = LIGHTONOFFPERIOD100
BLINK_YELLOW.Ratio = LIGHTONOFFRATIOP1V1

BLINK_WHITE = LightMode()
BLINK_WHITE.Color = WHITE
BLINK_WHITE.Period = LIGHTONOFFPERIOD100
BLINK_WHITE.Ratio = LIGHTONOFFRATIOP1V1

BLINK_CYAN = LightMode()
BLINK_CYAN.Color = CYAN
BLINK_CYAN.Period = LIGHTONOFFPERIOD100
BLINK_CYAN.Ratio = LIGHTONOFFRATIOP1V1

BLINK_MAGENTA = LightMode()
BLINK_MAGENTA.Color = MAGNETA
BLINK_MAGENTA.Period = LIGHTONOFFPERIOD100
BLINK_MAGENTA.Ratio = LIGHTONOFFRATIOP1V1

BLINK_COLORS = {
    "blue": BLINK_BLUE,
    "red": BLINK_RED,
    "green": BLINK_GREEN,
    "yellow": BLINK_YELLOW,
    "magenta": BLINK_MAGENTA,
    "cyan": BLINK_CYAN,
    "white": BLINK_WHITE,
}


LIGHT_HOUSE_COLORS = {
    "blue": 0,
    "yellow": 1,
    "red": 2,
    "green": 4,
    "magenta": 3,
    "cyan": 0,
    "white": 1,
}

ADDRESSES_CON = {
    "1": 1,
    "2": 2,
}


class XGateHandler:
    def __init__(self, xgate_address, *args, **kwargs):
        self.xgate = XGate(xgate_address)  # "192.168.0.10"
        self.ptltera = PtlTera()
        self.PtlIBS = PtlIBS()
        self.xgate.Buses[0].Devices.AddOrUpdate(self.ptltera)
        self.xgate.Buses[1].Devices.AddOrUpdate(self.PtlIBS)
        self.xgate.StartUnicastCommandQueue()
        # self.xgate.EnableLight = True
        self.active_lights = {
            1: [],
            2: [],
            3: [],
            4: [],
            5: [],
            6: [],
            7: [],
            11: [],
            12: [],
            13: [],
            14: [],
            15: [],
            16: [],
            17: [],
        }

        self.ptltera.IsLockedChanged += self.ptltera_islocked_changed
        self.ptltera.ExecuteProtocol += self.ptltera_excute_protocol
        self.ptltera.Error += self.ptltera_error
        self.ptltera.InErrorChanged += self.ptltera_error_changed
        self.clear_all_lights()
        self.clear_lhs()
        # self.xgate.InputPortStatusChanged += self.xgate_status_changed
        # self.xgate.AppearanceChanged += self.xgate_appearance_changed

    def xgate_appearance_changed(self, source, args):
        print("xgate appearance called!", source, args)

    def xgate_status_changed(self, source, args):
        pass
        # print('xgate status called!', source, args)

    def ptltera_islocked_changed(self, source, args):
        pass
        # print('tera is locked called!', source, args)

    def ptltera_error_changed(self, source, args):
        pass
        # print(' tera Error changed!', source, args)

    def ptltera_error(self, source, args):
        print("tera Error called!", source, args)

    def ptltera_excute_protocol(self, source, args):
        return
        print(
            "tera execute called!",
            source.CommandCount,
            source.Address,
            args.BeginTime,
            args.EndTime,
            args.Protocol,
            args.CommunicationClient,
        )

    def ptlps_excute_protocol(self, source, args):
        pass
        # print('my_handler called!', source.Address, args.BeginTime, args.EndTime, args.Protocol, args.CommunicationClient)

    def initiate_storage(self):
        pass

    def switch_lights(self, address, lamp, col, blink=True):
        # self.clear_lhs()
        if lamp in self.active_lights[address]:
            self.active_lights[address].remove(lamp)
        else:
            self.active_lights[address].append(lamp)

        lightmodes = List[LightMode]()
        for i in range(1, 101):
            lightmode = LightMode()
            if i in self.active_lights[address]:
                lightmode.Color = COLORS[col]
                lightmode.Period = LIGHTONOFFPERIOD200
                if blink:
                    lightmode.Ratio = LIGHTONOFFRATIOP1V1
                else:
                    lightmode.Ratio = LIGHTONOFFRATIOP1V0
            else:
                lightmode.Color = LIGHT_OFF
            lightmodes.Add(lightmode)
        time.sleep(0.5)
        self.ptltera.Address = address
        self.ptltera.Display(lightmodes)

        # time.sleep(0.1)
        # self.PtlIBS.Address = 19
        # for add in [1,2,11,12,3,4,5,6,7]:
        #     if len (self.active_lights[add]) > 0:
        #         #self.PtlIBS.Lighthouses[1].Display(LIGHTONOFFPERIOD200, LIGHTONOFFRATIOP1V1)
        #         self.PtlIBS.Lighthouses[0].Display(LIGHTONOFFPERIOD200, LIGHTONOFFRATIOP1V1)
        #         break

        # time.sleep(0.1)
        # self.PtlIBS.Address = 9
        # for add in [1,2,11,12,13,14,15,16,17]:
        #     if len (self.active_lights[add]) > 0:
        #         #self.PtlIBS.Lighthouses[1].Display(LIGHTONOFFPERIOD200, LIGHTONOFFRATIOP1V1)
        #         self.PtlIBS.Lighthouses[0].Display(LIGHTONOFFPERIOD200, LIGHTONOFFRATIOP1V1)
        #         break

    def clear_all_lights(self):
        lightmodes = List[LightMode]()
        for i in range(1, 101):
            lightmode = LightMode()
            lightmode.Color = LIGHT_OFF
            lightmodes.Add(lightmode)
        for address in [1, 2, 3, 4, 5, 6, 7, 11, 12, 13, 14, 15, 16, 17]:
            time.sleep(0.2)
            self.ptltera.Address = address
            self.ptltera.Clear()
            self.ptltera.Display(lightmodes)

    def clear_leds(self):
        for address in [1, 2, 3, 4, 5, 6, 7, 11, 12, 13, 14, 15, 16, 17]:
            if len(self.active_lights[address]) > 0:
                time.sleep(0.2)
                self.ptltera.Address = address
                self.ptltera.Clear()

        self.active_lights = {
            1: [],
            2: [],
            3: [],
            4: [],
            5: [],
            6: [],
            7: [],
            11: [],
            12: [],
            13: [],
            14: [],
            15: [],
            16: [],
            17: [],
        }

    def light_house_on(self, mode="normal"):
        time.sleep(0.5)
        self.PtlIBS.Address = 19

        if mode == "normal":
            self.PtlIBS.Lighthouses[2].Clear()
            self.PtlIBS.Lighthouses[4].Display(LIGHTONOFFPERIOD100, LIGHTONOFFRATIOP1V0)
        elif mode == "error":
            self.PtlIBS.Lighthouses[4].Clear()
            self.PtlIBS.Lighthouses[2].Display(LIGHTONOFFPERIOD100, LIGHTONOFFRATIOP1V0)

        time.sleep(0.5)
        self.PtlIBS.Address = 9
        if mode == "normal":
            self.PtlIBS.Lighthouses[2].Clear()
            self.PtlIBS.Lighthouses[4].Display(LIGHTONOFFPERIOD100, LIGHTONOFFRATIOP1V0)
        elif mode == "error":
            self.PtlIBS.Lighthouses[4].Clear()
            self.PtlIBS.Lighthouses[2].Display(LIGHTONOFFPERIOD100, LIGHTONOFFRATIOP1V0)

    def clear_lhs(self):
        for lh in [9, 19]:
            time.sleep(0.5)
            self.PtlIBS.Address = lh
            self.PtlIBS.Lighthouses[4].Clear()
            self.PtlIBS.Lighthouses[2].Clear()
            self.PtlIBS.Lighthouses[1].Clear()
            self.PtlIBS.Lighthouses[0].Clear()

    def test(self,step=False):
        xgate = self
        xgate.light_house_on()
        for i in [1,2,3,4,5,6,7,11,12,13,14,15,16,17]:
            for j in range(1,101):
                xgate.switch_lights(address=i,lamp=j,col="red",blink=False)
                print(f"ROW {i} lamp {j}")
                if step: input()
                time.sleep(0.25)
