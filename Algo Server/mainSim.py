import sys
import time
from typing import List
import pickle

import settings
from app import AlgoSimulator, AlgoMinimal
from entities.effects.direction import Direction
from entities.grid.obstacle import Obstacle

def parse_obstacle_data(data) -> List[Obstacle]:
    obs = []
    for obstacle_params in data:
        obs.append(Obstacle(obstacle_params[0],
                            obstacle_params[1],
                            Direction(obstacle_params[2]),
                            obstacle_params[3]))
    # [[x, y, orient, index], [x, y, orient, index]]
    return obs

obs = parse_obstacle_data([[145, 35, 180, 0], [115, 85, 0, 1], [25, 155, -90, 2], [175, 175, 180, 3], [105, 115, 180, 4]])
app = AlgoSimulator(obs)
app.init()
app.execute()