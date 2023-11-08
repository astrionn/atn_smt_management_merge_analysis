import random
import serial

class PTL_API:

    def __init__(self,port):
        self.port = port
        self.baudrate = 9600
        self.serial = serial.Serial(port=self.port,baudrate=self.baudrate,timeout=0.25)


    def _LED_Control(self,gateway=1,controller=1,command=11,channel=1,LED=1,R=255,G=0,B=0):
        
        led_C = int(str(LED).zfill(3)[0]) # hundred bit (123 -> 1)
        led_D = int(str(LED).zfill(3)[1:]) # decimal bit (123 -> 23)
        
        cmd = [
        2, #STX
        gateway,
        controller,
        command, #11 LED on, 21 LED Off, 22 Channel Off, 23 all off
        channel,
        led_C,
        led_D,
        R,
        G,
        B,
        0, #blink
        0 #reserved
        
        ]

        byte_cmd = bytes(cmd)
        query = self.serial.write(byte_cmd)
        res = self.serial.read(8)
    
ptl = PTL_API('COM6')
ptl._LED_Control(command=23,LED=0)
for i in [i for i in range(1,150) if i not in range(2,150,4)]:

    cmd = 11
    if i > 150:
        cmd = 21
        i -=150
    ptl._LED_Control(LED=i,R=random.randint(0,255),G=random.randint(0,255),B=random.randint(0,255),command=cmd)
else:
    ptl._LED_Control(command=23,LED=0)
