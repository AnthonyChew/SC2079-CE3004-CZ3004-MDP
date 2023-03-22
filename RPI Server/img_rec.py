import sys
sys.path.append('/usr/lib/python3/dist-packages')

from picamera import PiCamera
from sendtopc import *

#take pic and send to img rec server then return label 
def imgRec():
    camera = PiCamera()
    camera.resolution=(615,462)
    print("Taking photo 1...")
    camera.capture('/home/mdp28/imgRec/image1.jpg')
    camera.close()

    label = sendImgToPC()
    return label.strip().decode()
