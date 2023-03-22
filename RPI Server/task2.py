from multiprocessing import Process, Value, Queue, Manager, Lock
import string
import time
from datetime import datetime

# from RPI_PC import PcComm
from RPI_Android import AndroidComm
from RPI_STM import STMComm
from RPI_PC import PcComm
# from IP import ImageProcessor
from config import MESSAGE_SEPARATOR, LOCALE
from colorama import *
from img_rec import *

from picamera import PiCamera

import time

init(autoreset=True)

class MultiProcessCommunication:

    #Task 2 only need connection with STM and AND 
    def __init__(self):

        self.stm = STMComm()
        self.android = AndroidComm()

        self.manager = Manager()

        self.message_queue = self.manager.Queue()
        self.to_android_message_queue = self.manager.Queue()

        #Pre set movement for android 
        self.stmDic = {'W' : "W10" , 'A' : "Q90" , 'S' : "X10", 'D' : "E90", 'R' : 'R' , 'T' : 'T', 'F' : 'F','G' : 'G'}
        self.threePoint = {'R' : 'W12,Q90,X7' , 'T' : 'W6,E90,X9', 'G' : 'W9,C90,X2','F' : 'Z90,X15' }

        #Read threard for stm and android
        self.read_stm_process = Process(target=self._read_stm)
        self.read_android_process = Process(target=self._read_android)

        #Write threard for stm and android
        self.write_process = Process(target=self._write_target)
        self.write_android_process = Process(target=self._write_android)

        print(Fore.LIGHTGREEN_EX + '[MultiProcess] MultiProcessing initialized')

        self.img1 = None


    def start(self):
        try:
            # Connect to STM and Android
            self.stm.connect_stm()
            self.android.connect_android()

            #Start all read thread
            self.read_stm_process.start()
            self.read_android_process.start()

            #Start all write thread
            self.write_process.start()
            self.write_android_process.start()

            startComms_dt = datetime.now().strftime('%d-%b-%Y %H:%M%S')
            print(Fore.LIGHTGREEN_EX + str(startComms_dt) + '| [MultiProcess] Communications started. Reading from STM, Algorithm & Android')

        except Exception as e:
            print(Fore.RED + '[MultiProcess-START ERROR] %s' % str(e))
            raise e

        self._allow_reconnection()

    #Reconnect algo
    def _allow_reconnection(self):
        while True:
            try:

                if not self.read_android_process.is_alive():
                    self._reconnect_android()

                if not self.write_process.is_alive():
                    self.write_process.terminate()
                    self.write_process = Process(target=self._write_target)
                    self.write_process.start()

                if not self.write_android_process.is_alive():
                    self._reconnect_android()


            except Exception as e:
                print(Fore.RED + '[MultiProcess-RECONN ERROR] %s' % str(e))
                raise e

    #Reconnect method for STM
    def _reconnect_stm(self):
        self.stm.disconnect_stm()

        self.read_stm_process.terminate()
        self.write_android_process.terminate()

        self.stm.connect_stm()

        self.read_stm_process = Process(target=self._read_stm)
        self.read_stm_process.start()

        self.write_android_process = Process(target=self._write_android)
        self.write_android_process.start()

        print(Fore.LIGHTGREEN_EX + '[MultiProcess-RECONN] Reconnected to STM')

    #Reconnect method for Android
    def _reconnect_android(self):
        self.android.disconnect_android()

        self.read_android_process.terminate()
        self.write_android_process.terminate()

        self.android.connect_android()

        self.read_android_process = Process(target=self._read_android)
        self.read_android_process.start()

        self.write_android_process = Process(target=self._write_android)
        self.write_android_process.start()

        print(Fore.LIGHTGREEN_EX + '[MultiProcess-RECONN] Reconnected to Android')

    #Function to format message into dic[key:target] value:payload
    def _format_for(self, target, message):
        return {
            'target': target,
            'payload': message,
        }

    #Read stm method
    def _read_stm(self):
        #Loop reading msg from STM
        while True:
            try:
                raw_message = self.stm.read_from_stm()
                
                if raw_message is None or raw_message == b'':
                    print(Fore.LIGHTBLUE_EX + 'No Message from STM')
                    continue

                raw_message_list = raw_message.decode()
                print(raw_message.decode())
                
                #if message len is not 0
                if len(raw_message_list) != 0:
                    #split msg
                    message_list = raw_message_list.split(MESSAGE_SEPARATOR, 1)

                    #Check STM msg is for which target then push into message queue and payload
                    if message_list[0] == 'AND':

                        print(Fore.LIGHTCYAN_EX + 'STM > %s , %s' % (str(message_list[0]), str(message_list[1])))
                        self.to_android_message_queue.put_nowait(message_list[1].encode(LOCALE))

                    elif message_list[0] == 'ALG':
                        print(Fore.LIGHTCYAN_EX + 'STM > %s , %s' % (str(message_list[0]), str(message_list[1])))
                        self.message_queue.put_nowait(self._format_for(message_list[0], message_list[1].encode(LOCALE)))
                        
                    elif message_list[0] == 'RPI' and message_list[1] == 'SCAN\n':

                        #If STM send RPI:SCAN\n means take pic and tell STM all the next command
                        if(self.img1 == None):
                            print('scanning 1st image...')

                            #img rec func
                            label = imgRec() 
                            


                            #If label is no null
                            if label!='':
                                #RIGHT
                                if(str(label) == "38"):
                                    self.message_queue.put_nowait(self._format_for("STM", "v001".encode(LOCALE))) 
                                    self.message_queue.put_nowait(self._format_for("STM", "w500".encode(LOCALE))) 
                                    self.message_queue.put_nowait(self._format_for("STM", "q025".encode(LOCALE))) 
                                    self.message_queue.put_nowait(self._format_for("STM", "x001".encode(LOCALE))) 
                                #LEFT
                                elif(str(label) == "39"):
                                    self.message_queue.put_nowait(self._format_for("STM", "c001".encode(LOCALE))) 
                                    self.message_queue.put_nowait(self._format_for("STM", "w500".encode(LOCALE))) 
                                    self.message_queue.put_nowait(self._format_for("STM", "e020".encode(LOCALE))) 
                                    self.message_queue.put_nowait(self._format_for("STM", "x001".encode(LOCALE))) 

                                #Set img1
                                self.img1 = str(label)

                                #Add OBSTALCE:imgID to Android to update UI
                                self.to_android_message_queue.put_nowait("OBSTACLE:" + str(label))

                                print(Fore.LIGHTCYAN_EX + 'RPI > AND , %s' % ("OBSTACLE:" + str(label)))

                            else:
                                print(Fore.RED + 'No image detected!')
                            
                        elif(self.img1 != None):
                            print('scanning 2nd image...')

                            label = imgRec() 

                            if self.img1 == "38":
                                if str(label) == "38":
                                    print(Fore.RED + "RIGHT RIGHT")
                                    # Right after Right
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "a030".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "v001".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w005".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "q090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w038".encode(LOCALE))) #52
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "q090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w020".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "z001".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "q090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w008".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "e090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w500".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w011".encode(LOCALE)))
                                    self.img1 = None

                                elif str(label) == "39":
                                    # Left after Right
                                    # TO BE ADDED
                                    print(Fore.RED + "RIGHT LEFT")
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "q070".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w012".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "e091".encode(LOCALE)))
                                    # self.message_queue.put_nowait(
                                    #     self._format_for("STM", "w005".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "e091".encode(LOCALE)))
                                    # Outdoor
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w053".encode(LOCALE))) #53
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "e091".encode(LOCALE)))
                                    # Indoor
                                    # self.message_queue.put_nowait(
                                        # self._format_for("STM", "w45".encode(LOCALE)))
                                    # self.message_queue.put_nowait(
                                    #     self._format_for("STM", "e92".encode(LOCALE)))
                                    # self.message_queue.put_nowait(
                                    #     self._format_for("STM", "w005".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "z001".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "s020".encode(LOCALE)))#front too much
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "e090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "s005".encode(LOCALE)))#front too much
                                    # Indoor
                                    # self.message_queue.put_nowait(
                                    #     self._format_for("STM", "w11".encode(LOCALE)))
                                    # Outdoor
                                    # self.message_queue.put_nowait(
                                    #     self._format_for("STM", "w005".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "q090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w500".encode(LOCALE)))
                                    self.message_queue.put_nowait(self._format_for("STM", "w011".encode(LOCALE)))
                                    # # At the end to trigger stitch
                                    # self.message_queue.put_nowait(
                                    #     self._format_for("STM", "x001".encode(LOCALE)))
                                    self.img1 = None

                            elif self.img1 == "39":
                                # Right after left
                                if str(label) == "38":
                                    
                                    print(Fore.RED + "LEFT RIGHT")
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "e070".encode(LOCALE)))
                                    # self.message_queue.put_nowait(
                                    #     self._format_for("STM", "w024".encode(LOCALE))) in door
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w020".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "q090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w005".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "q090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w058".encode(LOCALE)))
                                    # self.message_queue.put_nowait(
                                    #     self._format_for("STM", "w060".encode(LOCALE))) outdoor
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "q090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w020".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "z001".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "q090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w005".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "e090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w500".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w011".encode(LOCALE)))
                                    self.img1 = None

                                elif str(label) == "39":
                                    print(Fore.RED + "LEFT LEFT")
                                    # Left after left
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "d030".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "c001".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w002".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "e090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w042".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "e090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w020".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "z001".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "e090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w008".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "q090".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w500".encode(LOCALE)))
                                    self.message_queue.put_nowait(
                                        self._format_for("STM", "w011".encode(LOCALE)))
                                    self.img1 = None
                                                # with lock:
                                                #     loopNext.value = 0
                                                #     moveNext.value -= 1
                                                
                            self.to_android_message_queue.put_nowait("OBSTACLE:" + str(label))
                            
                    else:
                        # Printing message without proper message format on RPi terminal for STM sub-team to debug
                        print(Fore.LIGHTBLUE_EX + '[Debug] Message from STM: %s' % str(message_list))

            except Exception as e:
                print(Fore.RED + '[MultiProcess-READ-STM ERROR] %s' % str(e))
                break

    #Read android method
    def _read_android(self):
        #Loop reading msg from AND
        while True:
            try:
                raw_message = self.android.read_from_android()

                if raw_message is None:
                    continue
                raw_message_list = raw_message.decode().splitlines()
                
                #Each line of msg from AND
                for pre_message_list in raw_message_list:
                    #If msg len is not 0
                    if len(pre_message_list) != 0:
                        
                        #Split msg
                        message_list = pre_message_list.split(MESSAGE_SEPARATOR, 1)

                        #Check msg target then append into AND queue or write queue
                        if  message_list[0] == 'STM':
                            
                            if(self.stmDic.get(message_list[1]) != None):
                                self.message_queue.put_nowait(self._format_for(message_list[0], self.stmDic[message_list[1]].encode(LOCALE))) 
                            else:
                                self.message_queue.put_nowait(self._format_for(message_list[0], message_list[1].encode(LOCALE))) 

                        elif message_list[0] == 'RPI':
                            #If recieve RPI:Start from AND send commnad to STM
                            if(message_list[1] == 'Start'):
                                self.img1 = None

                                #Make sure self.img1 is None
                                while(self.img1 != None):
                                    continue
                                
                                self.message_queue.put_nowait(self._format_for("STM", "w500".encode(LOCALE))) 
                                self.message_queue.put_nowait(self._format_for("STM", "x001".encode(LOCALE))) 
                            else:
                                print(Fore.GREEN + '[Debug] Message from AND: %s' % str(message_list[1]))
                        else:
                            print(Fore.LIGHTBLUE_EX + '[Debug] Message from AND: %s' % str(message_list))
                            self.message_queue.put_nowait(self._format_for(message_list[0], message_list[1].encode(LOCALE)))

            except Exception as e:
                print(Fore.RED + '[MultiProcess-READ-AND ERROR] %s' % str(e))
                break

    #Method to write to STM & AND 
    def _write_target(self):
        #Loop to check message queue if message queue is not empty send message
        while True:
            target = None
            try:
                if not self.message_queue.empty():
                    #Get first dic in queue
                    message = self.message_queue.get_nowait()

                    #Break down dic in queue to target and payload
                    target, payload = message['target'], message['payload']
                    
                    #Target = STM
                    if target == 'STM':
                            self.stm.write_to_stm(payload)
                            time.sleep(0.5) #Delay needed ..... somehow if no STM won't be able to recieve
                    #In case accidently put AND msg in this queue
                    elif target == 'AND':
                        self.android.write_to_android(payload)
            except Exception as e:
                print(Fore.RED + '[MultiProcess-WRITE-%s ERROR] %s' % (str(target), str(e)))
                break
    
    #Method to write to AND. Seperate out AND and STM so that things will be faster instead of just using one writing thread 
    def _write_android(self):
        while True:
            try:
                if not self.to_android_message_queue.empty():
                    message = self.to_android_message_queue.get_nowait()
                    self.android.write_to_android(message)
            except Exception as e:
                print(Fore.RED + '[MultiProcess-WRITE-AND ERROR] %s' % str(e))
                break

def init():
    try:
        #Init class and start
        multi = MultiProcessCommunication()
        multi.start()
    except Exception as err:
        print(Fore.RED + '[Main.py ERROR] {}'.format(str(err)))

if __name__ == '__main__':
    init()
