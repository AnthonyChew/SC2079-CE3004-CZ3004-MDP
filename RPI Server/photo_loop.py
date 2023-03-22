import time
from picamera import PiCamera
import os

camera = PiCamera()

print("Camere loop")


#for c in range(0,25):
time.sleep(1)
# files = next(os.walk("/home/mdp28/testPic/2_3"))[2]
# file_count = len(files) 			
#print("Taking photo " + str(file_count))
camera.capture("/home/mdp28/test.jpg")
print("Done.")
