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

    def __init__(self):

        self.stm = STMComm()
        self.algorithm = PcComm()
        self.android = AndroidComm()

        self.manager = Manager()

        self.message_queue = self.manager.Queue()
        self.to_android_message_queue = self.manager.Queue()

        
        self.stmDic = {'W' : "W10" , 'A' : "Q90" , 'S' : "X10", 'D' : "E90", 'R' : 'R' , 'T' : 'T', 'F' : 'F','G' : 'G'}
        self.threePoint = {'R' : 'W12,Q90,X7' , 'T' : 'W6,E90,X9', 'G' : 'W9,C90,X2','F' : 'Z90,X15' }

        self.lock = Lock()
        self.moveNext = Value('i', 0) # for STM to tell RPI it is ready for next command.
        self.loopNext = Value('i', 0) # for internal command like R,T,G,F for STM to tell RPI it is ready for next command.
        
        #Read STM theard with lock and race condition value moveNext and loopNext
        self.read_stm_process = Process(target=self._read_stm, args=(self.moveNext,self.loopNext,self.lock))
        #Read ALG and AND thread
        self.read_algorithm_process = Process(target=self._read_algorithm)
        self.read_android_process = Process(target=self._read_android)

        #Write STM & ALG theard with lock and race condition value moveNext and loopNext
        self.write_process = Process(target=self._write_target, args=(self.moveNext,self.loopNext,self.lock))
        #Write AND thread
        self.write_android_process = Process(target=self._write_android)
        print(Fore.LIGHTGREEN_EX + '[MultiProcess] MultiProcessing initialized')

        self.dropped_connection = Value('i', 0)

        self.sender = None

    def start(self):
        try:
            # Connect to STM, Algorithm (PC) and Android
            self.stm.connect_stm()
            self.algorithm.connect_PC()
            self.android.connect_android()

            # Start the process to read and write to various modules (STM, Algorithm [PC] and Android)
            self.read_stm_process.start()
            self.read_algorithm_process.start()
            self.read_android_process.start()

            self.write_process.start()
            self.write_android_process.start()
            startComms_dt = datetime.now().strftime('%d-%b-%Y %H:%M%S')
            print(Fore.LIGHTGREEN_EX + str(startComms_dt) + '| [MultiProcess] Communications started. Reading from STM, Algorithm & Android')


        except Exception as e:
            print(Fore.RED + '[MultiProcess-START ERROR] %s' % str(e))
            raise e

        self._allow_reconnection()

    #Reconnect algo if any connection is not alive start reconnect
    def _allow_reconnection(self):
        while True:
            try:
                if not self.read_algorithm_process.is_alive():
                    self._reconnect_algorithm()

                if not self.read_android_process.is_alive():
                    self._reconnect_android()

                if not self.write_process.is_alive():
                    self.write_process.terminate()
                    self.write_process = Process(target=self._write_target , args=(self.moveNext,self.loopNext,self.lock))
                    self.write_process.start()

                if not self.write_android_process.is_alive():
                    self._reconnect_android()


            except Exception as e:
                print(Fore.RED + '[MultiProcess-RECONN ERROR] %s' % str(e))
                raise e

    #Disconnect STM connection kill all read/write STM thread then reconnect and reinitlize all read/write thread
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

    #Disconnect ALG connection kill all read/write STM thread then reconnect and reinitlize all read/write thread
    def _reconnect_algorithm(self):
        self.algorithm.disconnect_PC()

        self.read_algorithm_process.terminate()

        self.algorithm.connect_PC()

        self.read_algorithm_process = Process(target=self._read_algorithm)
        self.read_algorithm_process.start()

        print(Fore.LIGHTGREEN_EX + '[MultiProcess-RECONN] Reconnected to Algorithm')

    #Disconnect AND connection kill all read/write STM thread then reconnect and reinitlize all read/write thread
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

    #Read STM loop 
    def _read_stm(self, moveNext, loopNext , lock):
        while True:
            try:
                raw_message = self.stm.read_from_stm()
                
                if raw_message is None or raw_message == b'':
                    print(Fore.LIGHTBLUE_EX + 'No Message from STM')
                    continue

                raw_message_list = raw_message.decode()
                print(raw_message.decode())
                
                if len(raw_message_list) != 0:

                    message_list = raw_message_list.split(MESSAGE_SEPARATOR, 1)

                    if message_list[0] == 'AND':
                        print(Fore.LIGHTCYAN_EX + 'STM > %s , %s' % (str(message_list[0]), str(message_list[1])))
                        self.to_android_message_queue.put_nowait(message_list[1].encode(LOCALE))

                    elif message_list[0] == 'ALG':
                        print(Fore.LIGHTCYAN_EX + 'STM > %s , %s' % (str(message_list[0]), str(message_list[1])))
                        self.message_queue.put_nowait(self._format_for(message_list[0], message_list[1].encode(LOCALE)))

                    #STM tells RPI movement is done sleep and reduce race condition value so that lock will be release
                    elif message_list[0] == 'RPI' and message_list[1] == 'd\n':
                        time.sleep(0.5)
                        with lock:
                            loopNext.value -= 1
                            moveNext.value -= 1
                    else:
                        # Printing message without proper message format on RPi terminal for STM sub-team to debug
                        print(Fore.LIGHTBLUE_EX + '[Debug] Message from STM: %s' % str(message_list))

            except Exception as e:
                print(Fore.RED + '[MultiProcess-READ-STM ERROR] %s' % str(e))
                break

    #Read ALG loop 
    def _read_algorithm(self):
        while True:
            try:
                raw_message = self.algorithm.read_from_pc()

                if raw_message is None:
                    continue

                raw_message_list = raw_message.decode().splitlines()

                for pre_message_list in raw_message_list:
                    #Any msg other for STM will only be print out 
                    if len(pre_message_list) != 0:

                        message_list = pre_message_list.split(MESSAGE_SEPARATOR, 1)
                        
                        #When ALG sends movement to STM 
                        if message_list[0] == 'STM':
                            
                            print(Fore.LIGHTCYAN_EX + 'Algo > %s , %s' % (str(message_list[0]), str(message_list[1])))

                            #Add movmenet one by one into queue sperated with ','
                            for char in message_list[1].split(','):
                                self.message_queue.put_nowait(self._format_for(message_list[0], char.encode(LOCALE))) 

                        else:
                            print(Fore.LIGHTBLUE_EX + '[Debug] Message from ALGO: %s' % str(message_list))

            except Exception as e:
                print(Fore.RED + '[MultiProcess-READ-ALG ERROR] %s' % str(e))
                break

    #Read AND loop 
    def _read_android(self):
        while True:
            try:
                raw_message = self.android.read_from_android()

                if raw_message is None:
                    continue
                raw_message_list = raw_message.decode().splitlines()

                for pre_message_list in raw_message_list:
                    if len(pre_message_list) != 0:

                        message_list = pre_message_list.split(MESSAGE_SEPARATOR, 1)

                        #Relaying MSG from AND to ALG or STM
                        if message_list[0] == 'ALG':
                            print(Fore.LIGHTCYAN_EX + 'Android > %s , %s' % (str(message_list[0]), str(message_list[1])))
                            self.message_queue.put_nowait(self._format_for(message_list[0], message_list[1].encode(LOCALE)))
                        elif  message_list[0] == 'STM':
                            #If msg is for STM and payload can be found in stmDic add write queue with those payload
                            if(self.stmDic.get(message_list[1]) != None):
                                self.message_queue.put_nowait(self._format_for(message_list[0], self.stmDic[message_list[1]].encode(LOCALE))) 
                            else:
                                #else custom command to STM
                                self.message_queue.put_nowait(self._format_for(message_list[0], message_list[1].encode(LOCALE))) 

                        else:
                            print(Fore.LIGHTBLUE_EX + '[Debug] Message from AND: %s' % str(message_list))
                            self.message_queue.put_nowait(self._format_for(message_list[0], message_list[1].encode(LOCALE)))

            except Exception as e:
                print(Fore.RED + '[MultiProcess-READ-AND ERROR] %s' % str(e))
                break


    def _write_target(self , moveNext , loopNext, lock):
        while True:
            target = None
            try:
                if not self.message_queue.empty():
                    message = self.message_queue.get_nowait()
                    target, payload = message['target'], message['payload']
                    if target == 'ALG':
                        self.algorithm.write_to_pc(payload)
                    elif target == 'STM':
                        with lock:
                            moveNext.value = 0
                            loopNext.value = 0

                        # ---If msg to SMT is P0 handle take picture on RPI instead of depending STM because reading STM for 'RPI:s\n' <- sometimes might miss ---
                        if(payload.decode() == 'P0'):
                            # --- checklist obstacle avoidance ---
                            # loopNext.value = 0       
                            # while True:
                            #     print('scanning image...')
                            #     self.to_android_message_queue.put_nowait('scanning image...'.encode(LOCALE))

                            #     label = imgRec() 

                            #     #label = self.algorithm.sendAndWaitPCReturn()
                            #     #label = label.split(MESSAGE_SEPARATOR, 1)

                            #     #send image id to AND
                            #     #if label!='' and label!='bullseye':
                            #     if label !=b'bullseye\n' and label != b'null' :
                            #         stringToAND = "OBSTACLE:" + str(label)
                            #         print(Fore.LIGHTCYAN_EX + 'RPI > AND , %s' % (stringToAND))

                            #         #send image id to ALG
                            #         print(Fore.LIGHTCYAN_EX + 'RPI > ALG , %s' % (str(label[1])))
                            #         self.message_queue.put_nowait(self._format_for("ALG", str(label[1]).encode(LOCALE)))
                            #         self.to_android_message_queue.put_nowait(stringToAND)
                            #         break
                            #     else:
                            #         commands = ['Z90','W70','Q90','W15x','Q90']
                            #         for command in commands:
                            #             self.stm.write_to_stm(command.encode(LOCALE))
                            #             self.to_android_message_queue.put_nowait(("MOVE:"+command).encode(LOCALE))

                            #             with lock:  
                            #                 loopNext.value += 1

                            #             while(loopNext.value > 0):
                            #                 continue
                            #print('scanning image...')
                            #self.to_android_message_queue.put_nowait('scanning image...'.encode(LOCALE))

                            #ImgRec func
                            label = imgRec() 

                            # --- attempt to do backwards if no img detected --- ***But got bug that command will be skip after doing this not sure why
                            #send image id to AND
                            #if label!='' and label!='bullseye':
                            # exitCount = 0 
                            # if(label == 'null'):
                            #     self.stm.write_to_stm("X10".encode(LOCALE))
                            #     with lock:  
                            #         loopNext.value += 1
                            #     while(loopNext.value > 0):
                            #             time.sleep(0.1)
                            #             if(exitCount < 100):
                            #                 continue
                            #             else:
                            #                 break
                            #     label = imgRec()
                                
                            #     self.stm.write_to_stm("W10".encode(LOCALE))

                            #     exitCount = 0 

                            #     with lock:  
                            #         loopNext.value += 1
                            #     while(loopNext.value > 0):
                            #             time.sleep(0.1)
                            #             if(exitCount < 100):
                            #                 exitCount += 1
                            #                 continue
                            #             else:
                            #                 break
                                        
                            self.to_android_message_queue.put_nowait("OBSTACLE:" + str(label))

                        elif payload.decode() == 'Stop':
                                statusSTM = "STATUS:" + payload.decode()
                                #print(Fore.LIGHTCYAN_EX + 'Algo > AND , %s' % (statusSTM))
                                self.message_queue.put_nowait(self._format_for("AND", statusSTM.encode(LOCALE)))
                        else:
                            #any other msg other than take pic or stop

                            #if payload can be found in threePoint dic 
                            if(self.threePoint.get(payload.decode()) != None):
                                
                                #Get commands from dic
                                commands = self.threePoint[payload.decode()]
                                
                                #Send command one by one to STM and wait for acknologement
                                for command in commands.split(','):
                                    #write to STM
                                    self.stm.write_to_stm(command.encode(LOCALE))

                                    #Increment lock with lock so it's atomic
                                    with lock:  
                                        loopNext.value += 1

                                    #Time out counter for 10 seconds
                                    exitCount = 0 

                                    #Wait till loopNext value is < 0 then stop waiting and send next command so that is not dead lock
                                    while(loopNext.value > 0):
                                        time.sleep(0.1)
                                        if(exitCount < 100):
                                            exitCount += 1
                                            continue
                                        else:
                                            break
                            else:
                                #else just write payload to STM
                                self.stm.write_to_stm(payload)


                            with lock:  
                                moveNext.value += 1

                            #Time out counter for 10 seconds
                            exitCount = 0 
                            
                           #Wait till loopNext value is < 0 then stop waiting and send next command so that is not dead lock
                            while(moveNext.value > 0):
                                time.sleep(0.1)
                                if(exitCount < 100):
                                    exitCount+=1
                                else:
                                    break

                            #Send movement done to AND at last to won't hog on important threads
                            if(payload.decode()[0] == 'W' or payload.decode()[0] == 'X'):
                                #Cause front is dynamic so went 
                                self.to_android_message_queue.put_nowait("MOVE:"+payload.decode()[:-1])
                            else:
                                self.to_android_message_queue.put_nowait("MOVE:"+payload.decode()[0])
                        
                    elif target == 'AND':
                        self.android.write_to_android(payload)
            except Exception as e:
                print(Fore.RED + '[MultiProcess-WRITE-%s ERROR] %s' % (str(target), str(e)))

                if target == 'STM':
                    self.dropped_connection.value = 0

                elif target == 'ALG':
                    self.dropped_connection.value = 1

                break
    
    #Write to anroid loop
    def _write_android(self):
        while True:
            try:
                if not self.to_android_message_queue.empty():
                    message = self.to_android_message_queue.get_nowait()
                    self.android.write_to_android(message)
                    #print(Fore.LIGHTGREEN_EX + '[Debug] Message from RPI: %s' % str(message))
            except Exception as e:
                print(Fore.RED + '[MultiProcess-WRITE-AND ERROR] %s' % str(e))
                break

def init():
    try:
        multi = MultiProcessCommunication()
        multi.start()
    except Exception as err:
        print(Fore.RED + '[Main.py ERROR] {}'.format(str(err)))

if __name__ == '__main__':
    init()
