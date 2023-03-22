# to be run on pc

#import datetime
#import struct
import socket
import sys
import threading
import requests
import os
import subprocess
from PIL import Image
from ultralytics import YOLO

import time
from typing import List
import pickle

import settings
from app import AlgoSimulator, AlgoMinimal
from entities.effects.direction import Direction
from entities.connection.rpi_client import RPiClient
from entities.connection.rpi_server import RPiServer
from entities.grid.obstacle import Obstacle

# --- constants ---
WIFI_PORT = 5001
# HOST = '192.168.45.208'   # IP address of server (PC)
HOST= '192.168.28.22'
#HOST= '192.168.50.251'
#HOST = '172.0.0.1'

# ---Dictionary to map Detected Values to their corresponding IDs---
algoDict = {
    'N' : 'W10' , 'E' : 'E45' , 'W' : 'Q45' , 'S' : 'X10' , 'P' : 'P' , 'Stop' : 'Stop'
}

PORT = WIFI_PORT  # Local port

# --- functions ---
def exit_prog(inp):
    if inp == "exit":
        sys.exit(0)


def get_detection(url, img_path):
    r = requests.get(url + '/img_rec', files = {
        'image': open(img_path, 'rb')
    })
    
    return r.json()

def parse_obstacle_data(data) -> List[Obstacle]:
    obs = []
    for obstacle_params in data:
        obs.append(Obstacle(obstacle_params[0],
                            obstacle_params[1],
                            Direction(obstacle_params[2]),
                            obstacle_params[3]))
    # [[x, y, orient, index], [x, y, orient, index]]
    return obs

def run_simulator():
    # Fill in obstacle positions with respect to lower bottom left corner.
    # (x-coordinate, y-coordinate, Direction)
    # obstacles = [[15, 75, 0, 0]]
    # obs = parse_obstacle_data(obstacles)
    obs = parse_obstacle_data([])
    app = AlgoSimulator(obs)
    app.init()
    app.execute()

def decision( data, run_simulator):

        # Obstacle list
        obstacles = parse_obstacle_data(data)
        if run_simulator:
            app = AlgoSimulator(obstacles)
            app.init()
            app.execute()
        app = AlgoMinimal(obstacles)
        app.init()
        app.execute()
        # Send the list of commands over.
        obs_priority = app.robot.hamiltonian.get_simple_hamiltonian()
        print(obs_priority)

        print("Sending list of commands to RPi...")
        commands = app.robot.convert_all_commands()
        commands.append("Stop")

        return commands
        


def handle_mdp(conn, addr):
    try:
        while True:
            print("Waiting for command: ")
            data = conn.recv(4096)

            if(data != None):
                command = data.decode()

                if 'OBS' in command:

                    #algo code here
                    print("Start Algo")
                    obsStr = command[3:]
                    data = []
                    for obs in obsStr.split(';'):
                        if(obs != ''):
                            tempData = []
                            for obsD in obs.split('-'):
                                tempData.append(obsD)
                            data.append(tempData)
                    print(data)
                    for i in range(len(data)):
                        data[i][0] = 10 * int(data[i][0]) + 5
                        # 200 - flip obstacle plot according to android
                        data[i][1] = (10 * int(data[i][1])) + 5
                        if data[i][2] == 'N':
                            data[i][2] = 90
                        elif data[i][2] == 'S':
                            data[i][2] = -90
                        elif data[i][2] == 'E':
                            data[i][2] = 0
                        elif data[i][2] == 'W':
                            data[i][2] = 180
                        data[i][3] = int(data[i][3])

                    command = ','.join(decision(data, True))
                    command = "STM:" + command
                    

                    while True:
                        print("Waiting for start command: ")
                        data = conn.recv(4096)
                        if(data != None):
                            dataSent = data.decode()
                            if('Start' in dataSent):
                                conn.sendall(command.encode())
                            
                            break
                    #wait for algo generated string 
                    # print("Input algo: ")
                    # algo = input()
                    # conn.sendall(("STM:"+algo).encode())
                    
                    #conn.sendall("STM:W5,W5,W5".encode())
                else:
                    print(data)
                
                time.sleep(5)
                
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
    # --- create socket ---
    print("Starting server")
    print('[DEBUG] create socket')
    results = ""

    # s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s = socket.socket()  # default value is (socket.AF_INET, socket.SOCK_STREAM) so you don't have to use it



    # solution for "[Error 89] Address already in use". Use before bind()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # --- assign socket to local IP (local NIC) ---

    print('[DEBUG] bind:', (HOST, PORT))

    s.bind((HOST, PORT))  # one tuple (HOST, PORT), not two arguments

    # --- set size of queue ---

    print('[DEBUG] listen')

    s.listen(1)  # number of clients waiting in queue for "accept".
                 # If queue is full then client can't connect.

    print('[DEBUG] Accept ... waiting')

    
    # --- accept client ---

    # accept client and create new socket `conn` (with different port) for this client only
    # and server will can use `s` to accept other clients (if you will use threading)
    conn, addr = s.accept()  # socket, address

    print('[DEBUG] Connected by:', addr)

    while True:
        handle_mdp(conn, addr)
    # while True:

    #     t = threading.Thread(target=handle_mdp, args=(conn, addr))
    #     t.start()
    #     t.join()

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
