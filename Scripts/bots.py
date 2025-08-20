import random
import pygame
import math
import numpy as np
from enum import Enum
from math import pi, cos, sin

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
BROWN = (139, 69, 19)


# Simulation settings
WIDTH, HEIGHT = 600, 600

# Food definitions
FOOD_CLUSTER = 10
FOOD_CLUSTER_RADIUS = 10
FOOD_COUNT = 100


# Ant definitions
ANT_COUNT = 50
ANT_SIZE = 2
ANT_SPEED = 1
ANT_FIND_FOOD_RADIUS = 10
ANT_FIND_NEST_RADIUS = 10
ANT_FOLLOW_SCENT_RADIUS = 3
ANT_FORAGING_RANGE = 250
ANT_FOOD_COST = 10
ANT_MAX_TURN_ANGLE = 5  # degrees

SCENT_THRESHOLD = 0.001  # Threshold for scent detection

class STATE(Enum):
    AT_NEST = 0
    FORAGING = 1
    RETURN_TO_NEST = 2


# Nest
NEST_SIZE = 10
NEST_X = WIDTH // 2
NEST_Y = HEIGHT // 2
NEST_SECTOR_ANGLE = 15
nest_food = 0

# Set up (global) food and scent markers
food = np.zeros((WIDTH, HEIGHT), dtype=int)
find_food = np.zeros((WIDTH, HEIGHT), dtype=float)
find_nest = np.zeros((WIDTH, HEIGHT), dtype=float)

# class Nest:
#     def __init__(self):
#         self.x = NEST_X
#         self.y = NEST_Y
#         self.size = NEST_SIZE
#         self.food = 0

#     def add_food(self, amount):
#         self.food += amount

#     def draw(self, display):
#         pygame.draw.circle(display, YELLOW, (self.x, self.y), self.size)



class Ant:
    def __init__(self):
        self.state = STATE.AT_NEST
        self.x = NEST_X
        self.y = NEST_Y
        self.heading = random.uniform(0, 360)
        self.food = 0
        self.foraging_timer = ANT_FORAGING_RANGE
        self.return_to_nest_timer = 0

    def update(self):
        global nest_food, food, find_food, find_nest
        self.update_scent()
        match self.state:
            case STATE.AT_NEST:
                # Randomly decide to forage
                if random.random() < 0.1:
                    self.state = STATE.FORAGING
                    self.heading = self.find_scent_trail(find_food)
            case STATE.FORAGING:
                if not self.detect_food(food):
                    self.follow_scent(find_food)
                self.move()
                self.foraging_timer -= 1
                if self.foraging_timer <= 0:
                    self.heading = (self.heading + 180) % 360
                    self.state = STATE.RETURN_TO_NEST
                    self.foraging_timer = ANT_FORAGING_RANGE
                    self.return_to_nest_timer = ANT_FORAGING_RANGE
            case STATE.RETURN_TO_NEST:
                if self.detect_nest():
                    nest_food += self.food
                    self.food = 0
                elif self.food == 0:
                    self.detect_food(food)
                
                self.follow_scent(find_nest)
                self.move()
                self.return_to_nest_timer -= 1

                
               
    def update_scent(self):
        # Update food scent
        fx0 = int(self.x)
        fx1 = min(fx0 + 1, WIDTH - 1)
        fy0 = int(self.y)
        fy1 = min(fy0 + 1, HEIGHT - 1)
        dx = self.x - fx0
        dy = self.y - fy0
        A00 = dx * dy
        A01 = dx * (1 - dy)
        A10 = (1 - dx) * dy
        A11 = (1 - dx) * (1 - dy)

        match self.state:
            case STATE.FORAGING:
                if self.foraging_timer > 0:
                    find_nest[fx0,fy0] += A00
                    find_nest[fx0,fy1] += A01
                    find_nest[fx1,fy0] += A10                
                    find_nest[fx1,fy1] += A11
            case STATE.RETURN_TO_NEST:
                if self.food > 0 and self.return_to_nest_timer > 0:
                    multipler = 1
                else:
                    multipler = 0
                find_food[fx0,fy0] = max(0, find_food[fx0,fy0] + multipler * A00)
                find_food[fx0,fy1] = max(0, find_food[fx0,fy1] + multipler * A01)
                find_food[fx1,fy0] = max(0, find_food[fx1,fy0] + multipler * A10)
                find_food[fx1,fy1] = max(0, find_food[fx1,fy1] + multipler * A11)

    def follow_scent(self, scent_map):
        ix = round(self.x)
        iy = round(self.y)
        dx = self.x - ix
        dy = self.y - iy
        # Look for the strongest scent in the vicinity
        adjust_heading = 0
        scent_strength_total = 0

        for offx in range(-ANT_FOLLOW_SCENT_RADIUS, ANT_FOLLOW_SCENT_RADIUS + 1):
            for offy in range(-ANT_FOLLOW_SCENT_RADIUS, ANT_FOLLOW_SCENT_RADIUS + 1):
                # Calculate distance from the ant to the scent point
                dist = math.sqrt((offx - dx)**2 + (offy - dy)**2)
                if dist > 0  and dist <= ANT_FOLLOW_SCENT_RADIUS:
                    angle = math.degrees(math.atan2(offy - dy, offx - dx))
                    angle = (angle - self.heading) % 360  # Get angle relative to ant heading
                    # Check bounds 
                    if (0 <= ix + offx < WIDTH) and (0 <= iy + offy < HEIGHT):
                        scent_strength = scent_map[ix + offx, iy + offy]/ (1+dist)
                        
                        if (0 < angle < 90):
                            adjust_heading += angle*scent_strength/90
                            scent_strength_total += scent_strength
                        elif (270 < angle < 360):
                            adjust_heading -= (360-angle)*scent_strength/90
                            scent_strength_total += scent_strength
        self.heading += ANT_MAX_TURN_ANGLE*adjust_heading/scent_strength_total if scent_strength_total > 0 else 0
        self.heading = self.heading % 360  # Normalize heading
            

    def find_scent_trail(self, scent_map):
        ix = round(NEST_X)
        iy = round(NEST_Y)
        dx = NEST_X - ix
        dy = NEST_Y - iy
        # Look for the strongest scent trail around the nest
        #heading = 0
        Nsec = int(360 / NEST_SECTOR_ANGLE)
        sec = np.zeros(Nsec, dtype=float)  # Scent strength in each sector
        search_radius = NEST_SIZE+ANT_FOLLOW_SCENT_RADIUS

        for offx in range(-search_radius, search_radius + 1):
            for offy in range(-search_radius, search_radius + 1):
                # Calculate distance from the ant to the scent point
                dist = math.sqrt((offx - dx)**2 + (offy - dy)**2)
                if dist > NEST_SIZE  and dist <= search_radius:
                    if (0 <= ix + offx < WIDTH) and (0 <= iy + offy < HEIGHT):
                        angle = math.degrees(math.atan2(offy - dy, offx - dx))
                        isector = int(angle // NEST_SECTOR_ANGLE)  # Determine sector
                        dsector = (angle % NEST_SECTOR_ANGLE)/NEST_SECTOR_ANGLE # Distance within sector
                        sec[isector] += (1-dsector)*scent_map[ix + offx, iy + offy]/(1+(dist-NEST_SIZE))
                        if isector < Nsec - 1:
                            sec[isector + 1] += dsector * scent_map[ix + offx, iy + offy]/(1+(dist-NEST_SIZE))
                        else:
                            sec[0] += dsector * scent_map[ix + offx, iy + offy]/(1+(dist-NEST_SIZE))
        # Find the sector with the strongest scent
        if max(sec) < SCENT_THRESHOLD:
            return random.uniform(0, 360)
        else:
            max_sector = np.argmax(sec)
            nextsec = (max_sector + 1) % Nsec
            prevsec = (max_sector - 1) % Nsec
            if sec[nextsec] > sec[prevsec]:
                heading = (sec[max_sector]*max_sector + sec[nextsec]*(max_sector+1)) / (sec[max_sector] + sec[nextsec])
            else:
                heading = (sec[max_sector]*max_sector + sec[prevsec]*(max_sector-1)) / (sec[max_sector] + sec[prevsec])
            # Calculate the heading towards the strongest sector
            heading = (NEST_SECTOR_ANGLE*heading + NEST_SECTOR_ANGLE/2 + np.random.normal(0, NEST_SECTOR_ANGLE/3)) % 360
            return heading

    def move(self): 
        self.x += ANT_SPEED * cos(math.radians(self.heading))
        self.y += ANT_SPEED * sin(math.radians(self.heading))
        # Detect edge of the screen and change direction
        if self.x < 0 or self.x >= WIDTH or self.y < 0 or self.y >= HEIGHT:
            self.heading = (self.heading + 180) % 360  # Turn around
            self.x = max(0, min(WIDTH-1, self.x))
            self.y = max(0, min(HEIGHT-1, self.y))

    def detect_nest(self):
        found_nest = False
        # Check if at nest
        if abs(self.x - NEST_X) < NEST_SIZE and abs(self.y - NEST_Y) < NEST_SIZE:
            found_nest = True
            self.state = STATE.AT_NEST
            self.heading = (self.heading + 180) % 360
            self.x = NEST_X
            self.y = NEST_Y
            self.foraging_timer = ANT_FORAGING_RANGE
            return found_nest
        else:
            # Check if within nest scent radius
            dx = self.x - NEST_X
            dy = self.y - NEST_Y
            dist = math.sqrt(dx**2 + dy**2)
            if dist <= NEST_SIZE + ANT_FIND_NEST_RADIUS:
                # Adjust heading towards the nest
                self.heading = (math.degrees(math.atan2(dy, dx)) +180) % 360
        return found_nest

    def draw(self, display):
        match self.state:
            case STATE.AT_NEST:
                color = YELLOW
            case STATE.FORAGING:
                color = YELLOW
            case STATE.RETURN_TO_NEST:
                if self.food > 0:
                    color = GREEN
                else:
                    color = BROWN
        pygame.draw.circle(display, color, (int(self.x), int(self.y)), ANT_SIZE)




    def detect_food(self, food):
        ix = round(self.x)
        ix = max(0, min(WIDTH-1, ix))  # Ensure within bounds
        iy = round(self.y)
        iy = max(0, min(HEIGHT-1, iy))  # Ensure within bounds
        #IF at food, collect and return to nest
        if food[ix, iy] > 0:
            self.food += 1
            food[ix, iy] -= 1
            self.state = STATE.RETURN_TO_NEST
            self.heading = (self.heading + 180) % 360
            self.foraging_timer = ANT_FORAGING_RANGE
            self.return_to_nest_timer = ANT_FORAGING_RANGE
            return
        # Look for food in the vicinity
        dx = self.x - ix
        dy = self.y - iy
        maxfood = 0
        found_food = False
        # Check if within foraging range of food
        for offx in range(-ANT_FIND_FOOD_RADIUS, ANT_FIND_FOOD_RADIUS + 1):
            for offy in range(-ANT_FIND_FOOD_RADIUS, ANT_FIND_FOOD_RADIUS + 1):
                # Check bounds  
                if (0 <= ix + offx < WIDTH) and (0 <= iy + offy < HEIGHT):  
                    dist = math.sqrt((offx-dx)**2 + (offy-dy)**2)
                    if food[ix+offx,iy+offy] > 0 and dist <= ANT_SPEED:
                        self.x = max(0, min(WIDTH-1, ix + offx))
                        self.y = max(0, min(HEIGHT-1, iy + offy))
                        self.food += 1
                        food[ix+offx, iy+offy] -= 1
                        self.state = STATE.RETURN_TO_NEST
                        self.heading = (self.heading + 180) % 360
                        self.foraging_timer = ANT_FORAGING_RANGE
                        self.return_to_nest_timer = ANT_FORAGING_RANGE
                        return
                                        
                    if dist <= ANT_FIND_FOOD_RADIUS:
                                            
                            if food[ix + offx, iy + offy]/(1+dist) > maxfood:
                                found_food = True
                                maxfood = food[ix + offx, iy + offy]/(1+dist)
                                bestheading = math.degrees(math.atan2(offy-dy, offx-dx))
        if found_food:
            #turn towards the food
            delta = (bestheading - self.heading) % 360
            if delta > 180:
                self.heading = (self.heading - min(delta,ANT_MAX_TURN_ANGLE)) % 360
            else:
                self.heading = (self.heading + min(delta,ANT_MAX_TURN_ANGLE)) % 360
        return found_food
                            
                        
                        

def main():

    global nest_food, food, find_food, find_nest
    
    pygame.init()
    display = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Ant Simulation")

    # Create ants
    ants = [Ant() for _ in range(ANT_COUNT)]
    
    # Distribute food in clusters
    for _ in range(FOOD_CLUSTER):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        for _ in range(FOOD_COUNT):
            food_x = int(np.random.normal(x, FOOD_CLUSTER_RADIUS))
            food_y = int(np.random.normal(y, FOOD_CLUSTER_RADIUS))
            food_x = max(0, min(WIDTH-1, food_x))
            food_y = max(0, min(HEIGHT-1, food_y))
            food[food_x, food_y] += 1

    



    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Blank screen
        display.fill((255, 255, 255))


        # Update food display
        map = np.zeros((WIDTH, HEIGHT, 3), dtype=np.uint8)
        map[:, :, 0] = 50*find_food  # Red channel
        map[:, :, 1] = 250*food  # Green channel
        map[:, :, 2] = 50*find_nest  # Blue channel
        surf = pygame.surfarray.make_surface(map) 


        display.blit(surf, (0, 0))
        # Draw nest
        pygame.draw.circle(display,YELLOW, (NEST_X, NEST_Y), NEST_SIZE)  

        for ant in ants:
            ant.update()
            ant.draw(display)

        if nest_food > ANT_FOOD_COST:
            nest_food -= ANT_FOOD_COST
            ants.append(Ant())

        # Update food and nest scent markers (decay over time)
        find_food *= 0.995
        find_food[find_food < SCENT_THRESHOLD] = 0
        find_nest *= 0.995
        find_nest[find_nest < SCENT_THRESHOLD] = 0
    
        Nfood = np.sum(food)
        Nant = len(ants)
        Nnes = sum(a.state == STATE.AT_NEST for a in ants)
        Nret = sum(a.state == STATE.RETURN_TO_NEST for a in ants)
        Nfor = sum(a.state == STATE.FORAGING for a in ants)

        pygame.display.update()
        pygame.display.set_caption("Ant Simulation, Food: {}, In nest: {}, Total ants: {}, At nest: {}, Foraging: {}, Returning: {}".format(Nfood, nest_food, Nant, Nnes, Nfor, Nret))

    pygame.quit()

if __name__ == "__main__":
    main()

