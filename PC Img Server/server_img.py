# to be run on pc

import socket
import sys
import threading
import time
import requests
import os
import subprocess
from PIL import Image as img
from ultralytics import YOLO
import PIL
import shutil, pathlib, fnmatch
import numpy as np

# --- constants ---
WIFI_PORT = 5000
HOST= '192.168.28.22'

# ---Dictionary to map Detected Values to their corresponding IDs---
IMG_MAP = {'one': '11', 'two': '12', 'three': '13', 'four': '14', 'five': '15', 'six': '16', 'seven': '17',
           'eight': '18', 'nine': '19',
           "AlphabetA": '20', "AlphabetB": '21', "AlphabetC": '22', "AlphabetD": '23', "AlphabetE": '24',
           "AlphabetF": '25', "AlphabetG": '26',
           "AlphabetH": '27', "AlphabetS": '28', "AlphabetT": '29', "AlphabetU": '30', "AlphabetV": '31',
           "AlphabetW": '32', "AlphabetX": '33',
           "AlphabetY": '34', "AlphabetZ": '35', "UpArrow": '36', "DownArrow": '37', "RightArrow": '38',
           "LeftArrow": '39', "Stop": '40', "VisualMarker": 'bullseye'}


PORT = WIFI_PORT  # Local port

# --- functions ---
def handle_mdp(conn, addr):
    try:
        #Loop to wait for any data to send to img server
        while True:

            print("Waiting for data:")

            #Reads 16384 bits every loop 
            data = conn.recv(16384)

            #When data is not empty
            if(data != None ):
                #First bytes of data
                picBytes = data
                print("Receiving image file..")
                
                #Keep appending picByte until the last 2 hex is 0xffxd9 means then image ended
                while data[-2:] != b'\xff\xd9':
                    picBytes += data
                    data = conn.recv(16384)
                
                #Appending the last bytes if data to picByte
                picBytes += data

                 #Create and replace if file exist to write picBytes to the file then close writer
                f = open('C:/Users/antho/OneDrive/Desktop/mdp/Raspi_Connection/imgRec/img0.jpg', 'wb') 
                f.write(picBytes)
                f.close()

                print("Image received") 

                #YOLOv8 img rec modal
                model = YOLO("C:/Users/antho/OneDrive/Desktop/mdp/Raspi_Connection/RpiMultiThread/best_GrayScale.pt")

                #Precit using the YOLOv8 modal
                results = model.predict(stream=True, imgsz=640, source='C:/Users/antho/OneDrive/Desktop/mdp/Raspi_Connection/imgRec/imgimg0.jpg', save=True, conf = 0.25)           

                resultsSTR = 'null'
                
                #Find img with the largest box border then append it to resultsSTR
                area = []
                for r in results: 
                    for i in range(0, len(r.boxes)): 
                        imageArea = r.boxes.xywhn[i][3] * r.boxes.xywhn[i][2] 
                        detachedArea = imageArea.item() 
                        area.append(detachedArea) 
                    if(len(area) == 0):
                        print("No image detected!")
                        resultsSTR = 'null'
                    else:
                        biggestIndex = np.argmax(area) 
                        resultsSTR = str(IMG_MAP[model.names[int(r.boxes.cls[biggestIndex])]])

                #Send the result to RPI 
                conn.sendall(resultsSTR.encode())
                print("Msg sent to RPI: " + resultsSTR)

                #Img Snitching stuff move img from run/detect to preset folder Test Folder For Snitch then snitch
                relevant_path_file = "C:/Users/antho/OneDrive/Desktop/mdp/Raspi_Connection/RpiMultiThread/runs/detect" 
                included_names = ['predict']
                file_names_predict = [fn for fn in os.listdir(relevant_path_file)
                            if any(fn.startswith(ext) for ext in included_names)]
                
                file_names_length = len((file_names_predict))
                if(file_names_length == 1):
                    file_names_length = ''
                    
                source_dir = "C:/Users/antho/OneDrive/Desktop/mdp/Raspi_Connection/RpiMultiThread/runs/detect/predict" + str(file_names_length)
                target_dir = "C:/Users/antho/OneDrive/Desktop/mdp/Raspi_Connection/RpiMultiThread/Test Folder For Snitch"

                def move_dir(src: str, dst: str, pattern: str = '*'):
                    if not os.path.isdir(dst):
                        pathlib.Path(dst).mkdir(parents=True, exist_ok=True)
                    for f in fnmatch.filter(os.listdir(src), pattern):
                        shutil.move(os.path.join(src, f), os.path.join(dst, f))
                        
                move_dir(source_dir,target_dir)
                        
                os.chdir('C:/Users/antho/OneDrive/Desktop/mdp/Raspi_Connection/RpiMultiThread/Test Folder For Snitch')
                print(os.getcwd())
                os.rename('C:/Users/antho/OneDrive/Desktop/mdp/Raspi_Connection/RpiMultiThread/Test Folder For Snitch/img0.jpg', 'C:/Users/antho/OneDrive/Desktop/mdp/Raspi_Connection/RpiMultiThread/Test Folder For Snitch/img' + str(len(os.listdir('C:/Users/antho/OneDrive/Desktop/mdp/Raspi_Connection/RpiMultiThread/Test Folder For Snitch'))) + '.jpg')
                print(os.getcwd())

                relevant_path = "C:/Users/antho/OneDrive/Desktop/mdp/Raspi_Connection/RpiMultiThread/Test Folder For Snitch"
                included_extensions = ['jpg','jpeg', 'bmp', 'gif']
                file_names = [fn for fn in os.listdir(relevant_path)
                    if any(fn.endswith(ext) for ext in included_extensions)]

                images = [img.open(x) for x in file_names]
                widths, heights = zip(*(i.size for i in images))

                total_width = sum(widths)
                max_height = max(heights)

                new_im = img.new('RGB', (total_width, max_height))

                x_offset = 0
                for im in images:
                    new_im.paste(im, (x_offset,0))
                    x_offset += im.size[0]

                new_im.save('test1.png')
                os.chdir('C:/Users/antho/OneDrive/Desktop/mdp/Raspi_Connection/RpiMultiThread')

                
    except BrokenPipeError:
        print('[DEBUG] addr:', addr, 'Connection closed by client?')
    except Exception as ex:
        print('[DEBUG] addr:', addr, 'Exception:', ex, ex.__traceback__)
    except KeyboardInterrupt as ex:
        conn.close()
        print('END')
    finally:
        conn.close()
            

# --- main ---
try:
    # Remove all img when running img server in snitch
    folder = "C:/Users/antho/OneDrive/Desktop/mdp/Raspi_Connection/RpiMultiThread/Test Folder For Snitch"
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


    # --- create socket ---
    print("Starting server")
    print('[DEBUG] create socket')

    s = socket.socket()  # default value is (socket.AF_INET, socket.SOCK_STREAM) so you don't have to use it

    # solution for "[Error 89] Address already in use". Use before bind()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # --- assign socket to local IP (local NIC) ---
    print('[DEBUG] bind:', (HOST, PORT))
    s.bind((HOST, PORT))  # one tuple (HOST, PORT), not two arguments

    print('[DEBUG] listen')

    s.listen(1)  # number of clients waiting in queue for "accept".
                 # If queue is full then client can't connect.

    print('[DEBUG] Accept ... waiting')

    #Loop to wait for one time connection then close socket after one img rec
    while True:
        # --- accept client ---

        # accept client and create new socket `conn` (with different port) for this client only
        # and server will can use `s` to accept other clients (if you will use threading)
        conn, addr = s.accept()  # socket, address

        print('[DEBUG] Connected by:', addr)

        #Create and start a thread
        t = threading.Thread(target=handle_mdp, args=(conn, addr))
        t.start()

except Exception as ex:
    print(ex)
except KeyboardInterrupt as ex:
    print(ex)
except:
    print(sys.exc_info())
finally:
    # --- close socket ---
    print('[DEBUG] close socket')
    s.close()
