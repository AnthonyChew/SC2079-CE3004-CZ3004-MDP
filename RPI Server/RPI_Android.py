import socket
import bluetooth
import os

from config import RFCOMM_CHANNEL, UUID, ANDROID_SOCKET_BUFFER_SIZE
from colorama import *

init(autoreset=True)

class AndroidComm:
    def __init__(self):
        self.server = None #RFcomm server
        self.client = None #RFcomm client
        
        #Make bluetooth discoverable 
        os.system('sudo hciconfig hci0 piscan')

        #Bluetooth RFcomm config
        self.server = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        self.server.bind(('', bluetooth.PORT_ANY))
        self.server.listen(RFCOMM_CHANNEL)#
        self.port = self.server.getsockname()[1]

        #Advertise bluettoh service with UUID,port and profile
        bluetooth.advertise_service(
            self.server, 'Mdp28_BT',
            service_id=UUID,
            service_classes=[UUID, bluetooth.SERIAL_PORT_CLASS],
            profiles=[bluetooth.SERIAL_PORT_PROFILE],
        )
        print(Fore.LIGHTYELLOW_EX + '[BT] Waiting for BT connection on RFCOMM channel %d' % self.port)

    #Loop until connection to android is establish
    def connect_android(self):
        while True:
            retry = False

            try:
                print(Fore.LIGHTYELLOW_EX + '[AND-CONN] Connecting to Android...')

                if self.client is None:
                    self.client, address = self.server.accept()
                    print(Fore.LIGHTGREEN_EX + '[AND-CONN] Successful connected with Android: %s ' % str(address))
                    retry = False

            except Exception as e:
                print(Fore.RED + '[AND-CONN ERROR] %s' % str(e))

                if self.client is not None:
                    self.client.close()
                    self.client = None

                retry = True

            if not retry:
                break

            print(Fore.LIGHTYELLOW_EX + '[AND-CONN] Retrying connection with Android...')

    #Disconnect RFcomm client method
    def disconnect_android(self):
        try:
            if self.client is not None:
                self.client.shutdown(socket.SHUT_RDWR)
                self.client.close()
                self.client = None
                print(Fore.LIGHTWHITE_EX + '[AND-DCONN] Disconnecting Client Socket')

        except Exception as e:
            print(Fore.RED + '[AND-DCONN ERROR] %s' % str(e))

    #Disconnect RFcomm client and server method
    def disconnect_all(self):
        try:
            if self.client is not None:
                self.client.shutdown(socket.SHUT_RDWR)
                self.client.close()
                self.client = None
                print(Fore.LIGHTWHITE_EX + '[AND-DCONN] Disconnecting Client Socket')

            if self.server is not None:
                self.server.shutdown(socket.SHUT_RDWR)
                self.server.close()
                self.server = None
                print(Fore.LIGHTWHITE_EX + '[AND-DCONN] Disconnecting Server Socket')

        except Exception as e:
            print(Fore.RED + '[AND-DCONN ERROR] %s' % str(e))

    #Read from android method
    def read_from_android(self):
        try:
            msg = self.client.recv(ANDROID_SOCKET_BUFFER_SIZE).strip()
            # print('Transmission from Android:')
            # print('\t %s' % msg)

            if msg is None:
                return None

            if len(msg) > 0:
                return msg

            return None

        except bluetooth.BluetoothError as e:
            print(Fore.RED + '[AND-READ ERROR] %s' % str(e))
            raise e

    #Write to android method
    def write_to_android(self, message):
        try:
            # print('Transmitted to Android:')
            # print('\t %s' % message)
            self.client.send(message)

        except bluetooth.BluetoothError as e:
            print(Fore.RED + '[AND-WRITE ERROR] %s' % str(e))
            raise e

#Main test 
if __name__ == '__main__':
     ser = AndroidComm()
     ser.connect_android()

     while True:
         try:
             print('In Loop')
             msg1 = ser.read_from_android()
             print("Msg from android:",msg1)
             msg2 = input("Msg to android:")
             ser.write_to_android(msg2)
         except KeyboardInterrupt:
             print('Android communication interrupted.')
             ser.disconnect_android()
             break

