import socket
import time

from config import WIFI_IP, ALGORITHM_SOCKET_BUFFER_SIZE, LOCALE ,WIFI_LOCAL_IP , IMG_WIFI_PORT
from colorama import *
from img_rec import *

from picamera import PiCamera

init(autoreset=True)


class ImgComm:
    def __init__(self):
        #init camera
        self.camera = PiCamera()
        #set camera resolution
        self.camera.resolution=(615,462)

        self.connect = None
        self.client = None

        self.connect = socket.socket()

    def connect_Img(self):
        while True:
            retry = False

            try:
                print(Fore.LIGHTYELLOW_EX + '[ALG-CONN] Listening for PC connections...')

                if self.client is None:

                    #testing
                    #self.connect.connect((WIFI_IP,WIFI_PORT))

                    #deploy
                    self.connect.connect((WIFI_LOCAL_IP,IMG_WIFI_PORT))

                    self.client = True
                    print(Fore.LIGHTGREEN_EX + '[ALG-CONN] Successfully connected with PC: %s' % str(self.connect))
                    retry = False

            except Exception as e:
                print(Fore.RED + '[ALG-CONN ERROR] %s' % str(e))

                if self.client is not None:
                    self.client.close()
                    self.client = None
                retry = True

            if not retry:
                break

            print(Fore.LIGHTYELLOW_EX + '[ALG-CONN] Retrying connection with PC...')
            time.sleep(1)

    def disconnect_Img(self):
        try:
            if self.client is not None:
                self.connect.close()
                self.client = None
                self.connect = socket.socket()
                print(Fore.LIGHTWHITE_EX + '[ALG-DCONN] Disconnecting Client Socket')

        except Exception as e:
            print(Fore.RED + '[ALG-DCONN ERROR] %s' % str(e))

    def read_from_img(self):
        try:
            data = self.connect.recv(ALGORITHM_SOCKET_BUFFER_SIZE).strip()
            # print('Transmission from PC:')
            # print('\t %s' % data)

            if len(data) > 0:
                return data

            return None

        except Exception as e:
            print(Fore.RED + '[ALG-READ ERROR] %s' % str(e))
            raise e

    def write_to_img(self, message):
        try:
            # print('Transmitted to PC:')
            # print('\t %s' % message)
            self.connect.send(message)

        except Exception as e:
            print(Fore.RED + '[ALG-WRITE ERROR] %s' % str(e))
            raise e

    def sendAndWaitPCReturn(self):
        #Take and save picture to path
        print("Taking photo 1...")
        self.camera.capture('/home/mdp28/imgRec/image1.jpg')

        try:
            #File to send to PC
            f = open('/home/mdp28/imgRec/image1.jpg','rb')

            print('Sending...')
            #Read 4096 bits from file until file ends
            data = f.read(4096)
            while data != bytes(''.encode()):
                self.connect.sendall(data)
                data = f.read(4096)

            print("IMG sent")

            #Read label return from PC
            while True:
                label = self.connect.recv(1024)
                if(label != None):
                    print("Reading: " + label.decode())
                    self.connect.close()   
                    return label.decode()

        except Exception as e:
            print(e)
        except KeyboardInterrupt as e:
            print(e)

if __name__ == '__main__':
     ser = ImgComm()
     ser.connect_Img()
     print('Connection established')
     
     while True: 
        try:
            #counter = 0
            print('Input command')
            command = input()
            if(command == "pic"):
                label = ser.sendAndWaitPCReturn()
                if(label != None):
                    print("Msg from Img Rec: " + label.decode())
                #counter+=1;
            else:
                continue
        except KeyboardInterrupt:
            print('Communication interrupted')
            ser.disconnect_PC()
            break
