import socket
import time

from config import WIFI_IP, WIFI_PORT, ALGORITHM_SOCKET_BUFFER_SIZE , WIFI_LOCAL_IP
from colorama import *
from img_rec import *

init(autoreset=True)


class PcComm:
    def __init__(self):

        self.connect = None
        self.client = None

        self.connect = socket.socket()

    #Loop till connection establish with ALG Server
    def connect_PC(self):
        while True:
            retry = False

            try:
                print(Fore.LIGHTYELLOW_EX + '[ALG-CONN] Listening for PC connections...')

                if self.client is None:

                    #deploy
                    self.connect.connect((WIFI_IP,WIFI_PORT))

			        #testing
                    #self.connect.connect((WIFI_LOCAL_IP,WIFI_PORT))

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

    #Disconnect to ALG Server
    def disconnect_PC(self):
        try:
            if self.client is not None:
                self.connect.close()
                self.client = None
                self.connect = socket.socket()
                print(Fore.LIGHTWHITE_EX + '[ALG-DCONN] Disconnecting Client Socket')

        except Exception as e:
            print(Fore.RED + '[ALG-DCONN ERROR] %s' % str(e))

    #Read from ALG server
    def read_from_pc(self):
        try:
            data = self.connect.recv(ALGORITHM_SOCKET_BUFFER_SIZE).strip()

            if len(data) > 0:
                return data

            return None

        except Exception as e:
            print(Fore.RED + '[ALG-READ ERROR] %s' % str(e))
            raise e

    #Write to ALG server
    def write_to_pc(self, message):
        try:
            self.connect.send(message)

        except Exception as e:
            print(Fore.RED + '[ALG-WRITE ERROR] %s' % str(e))
            raise e

#Main func to test ALG connection
if __name__ == '__main__':
    #  ser = PcComm()
    #  ser.connect_PC()
    #  print('Connection established')
    
    #testing img rec functionality 
    while True: 
        try:
            print('Input command')
            command = input()
            if(command == "pic"):
                label = imgRec()
                if(label != None):
                    print("Msg from Img Rec: " + label)
                continue
        except KeyboardInterrupt:
            print('Communication interrupted')
            # ser.disconnect_PC()
            break
