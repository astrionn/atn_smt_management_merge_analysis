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
    
#ptl = PTL_API('COM16')
#ptl._LED_Control(command=23,LED=0)
#ptl._LED_Control(LED=1)


"""
skip:
3
4
6
7
9
10
12
13
"""
vals = []
for i in range(1,150):
    if i<50 and i not in [1] + list(range(2,50,3)):
        continue
    if i > 49 and i < 100 and i not in list(range(50,100,3)):
        continue
    if i > 100 and i not in list(range(100,150,3)):
        continue
    vals.append(i)
    #ptl._LED_Control(LED=i,R=random.randint(0,255),G=random.randint(0,255),B=random.randint(0,255),command=cmd)
    r = 255 if i%3 == 0 else 0
    g = 255 if i%3 == 1 else 0
    b = 255 if i%3 == 2 else 0
    #ptl._LED_Control(LED=i,R=r,G=g,B=b,command=cmd)
    print(str(i).zfill(3),str(r).zfill(3),str(g).zfill(3),str(b).zfill(3))
else:
    #ptl._LED_Control(command=23,LED=0)
    pass
print(vals)