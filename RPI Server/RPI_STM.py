import serial
import time
from multiprocessing import Process

from RPI_PC import PcComm

from config import SERIAL_PORT, BAUD_RATE
from colorama import *

init(autoreset=True)


class STMComm:

    #Set port , baud rate 
    def __init__(self):
        self.port = SERIAL_PORT
        self.baud_rate = BAUD_RATE
        self.stm_connection = None

    #Loop till connection established
    def connect_stm(self):
        print(Fore.LIGHTYELLOW_EX + '[ARD-CONN] Waiting for serial connection...')
        while True:
            retry = False

            try:
                self.stm_connection = serial.Serial(self.port, self.baud_rate ,parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,bytesize=serial.EIGHTBITS)

                if self.stm_connection is not None:
                    print(Fore.LIGHTGREEN_EX + '[ARD-CONN] Successfully connected with STM: %s' % str(self.stm_connection.name))
                    retry = False

            except Exception as e:
                print(Fore.RED + '[ARD-CONN ERROR] %s' % str(e))
                retry = True

            if not retry:
                break

            print(Fore.LIGHTYELLOW_EX + '[ARD-CONN] Retrying connection with STM...')
            time.sleep(1)

    #Disconnect STM
    def disconnect_stm(self):
        try:
            if self.stm_connection is not None:
                self.stm_connection.close()
                self.stm_connection = None
                print(Fore.LIGHTWHITE_EX + '[ARD-DCONN ERROR] Successfully closed connection')

        except Exception as e:
            print(Fore.RED + '[ARD-DCONN ERROR] %s' % str(e))

    #rRead STM with delay
    def read_from_stm(self):
        try:
            self.stm_connection.flushInput()
            time.sleep(0.15)

            get_message = self.stm_connection.readline()

            if len(get_message) > 0:
                return get_message

            return None

        except Exception as e:
            print(Fore.RED + '[ARD-READ ERROR] %s' % str(e))
            raise e

    #Write to STM
    def write_to_stm(self, message):
        try:
            if self.stm_connection is None:
                print(Fore.LIGHTYELLOW_EX + '[ARD-CONN] STM is not connected. Trying to connect...')
                self.connect_stm()

            self.stm_connection.flushOutput()

            self.stm_connection.write(message + b'\r\n')

            print('Written to STM: %s' %str(message))

        except Exception as e:
            print(Fore.RED + '[ARD-WRITE Error] %s' % str(e))
            raise e
        

#Main func to test read write to STM
if __name__ == '__main__':

    ser = STMComm()
    ser.connect_stm()

    def _read_stm():
        while True:
            print("Waiting from STM")
            print(ser.read_from_stm())

     
    read_stm_process = Process(target=_read_stm )
    read_stm_process.start()


    while True:
        try:
            print("Enter command:")
            userInput = input()
            ser.write_to_stm(userInput.encode())

            
        except KeyboardInterrupt:
            print('Serial Communication Interrupted.')
            ser.disconnect_stm()
            break

