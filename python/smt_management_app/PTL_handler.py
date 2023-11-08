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
    
ptl = PTL_API('COM16')
ptl._LED_Control(command=23,LED=0)
#ptl._LED_Control(LED=1)

def test(all=False):
    vals = [1, 2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35, 38, 41, 42, 45, 48, 51, 54, 57, 60, 63, 66, 69, 71, 73, 76, 79, 82, 85, 88, 91, 94, 97, 99, 99, 102, 105, 108, 111, 114, 117, 120, 123, 126, 129, 132, 135, 138, 140]
    if all:
        vals = list(range(1,140))
    for j,i in enumerate(vals):
        r = 255 if j%3 == 2 else 0
        g = 255 if j%3 == 1 else 0
        b = 255 if j%3 == 0 else 0
        ptl._LED_Control(LED=i,R=r,G=g,B=b,command=11)
"""    
    for i in range(1,150):
        lim1 = 44
        lim2 = 72
        lim3 = 100
        lim4 = 156
        r,g,b = 0,0,0
        
        
        if i<lim1 and i not in [1] + list(range(2,lim1,3)):
            continue
        if i > lim1-1 and i < lim2 and i not in list(range(lim1,lim2,3)):
            continue
        if i > lim2-1 and i < lim3 and i not in list(range(lim2,lim3,3)):
            continue
        if i > lim3-1 and i < lim4 and i not in list(range(lim3,lim4,3)):
            continue

        if i < lim1: r = 255    
        if i > lim1-1 and i < lim2:
            g = 255
            i -=2
        if i > lim2-1 and i < lim3:
            b = 255
            i+=1
        if i > lim3-1 and i <lim4:
            r = 255
            g = 255
            i -=1
        vals.append(i)
        #ptl._LED_Control(LED=i,R=random.randint(0,255),G=random.randint(0,255),B=random.randint(0,255),command=cmd)
        
        ptl._LED_Control(LED=i,R=r,G=g,B=b,command=11)
        print(str(i).zfill(3),str(r).zfill(3),str(g).zfill(3),str(b).zfill(3))
    else:
        #ptl._LED_Control(command=23,LED=0)
        pass
    vals.append(71)
    print(sorted(vals))

"""
