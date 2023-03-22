import struct
import socket
import sys
import threading
import time

from config import WIFI_LOCAL_IP , IMG_WIFI_PORT, IMG_WIFI_LOCAL_IP
from multiprocessing import Process, Value, Queue, Manager, Lock

from picamera import PiCamera

# --- constants ---
HOST = WIFI_LOCAL_IP   # deploy (local or external) address IP of remote server 
#HOST = IMG_WIFI_LOCAL_IP # testing IP
PORT = IMG_WIFI_PORT # (local or external) port of remote server

def sendImgToPC():
    
    def sender(s):
        
        f = open(f'/home/mdp28/imgRec/image1.jpg','rb')

        print('Sending...')
        
        data = f.read(16384)
        while data != bytes(''.encode()):
            s.sendall(data)
            data = f.read(16384)
        
        print("IMG sent")

    try:
        # --- create socket ---
        s = socket.socket()         
        s.connect((HOST, PORT))

        # --- send and wait from reply from img rec server ---
        sender(s)
        while True:
            label = s.recv(1024)
            if(label != None):
                print("Reading: " + label.decode())
                s.close()   
                return label

    except Exception as e:
        print(e)
    except KeyboardInterrupt as e:
        print(e)
    except:
        print(sys.exc_info())

