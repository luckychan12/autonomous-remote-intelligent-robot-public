"""Top level main file for running the application"""

# imports
import logging
import sys
import time

import ThunderBorg3 as ThunderBorg  # conversion for python 3
from algorithms.algorithm import D_Star_Lite, Graph, Grid, Node
from hcsr04 import HCSR04
from mpu6050 import MPU6050
from robot.accelerometer import perform_drive
from robot.drive import calculate_angle, follow, pathing
from robot.gyroscope import perform_spin

# Setup the ThunderBorg
TB = ThunderBorg.ThunderBorg()

i2cAddress = TB.i2cAddress

# i2cAddress = ( 0x15  # Uncomment and change the value if you have changed the board address)
TB.Init()

if not TB.foundChip:
    boards = ThunderBorg.ScanForThunderBorg()
    if len(boards) == 0:
        logging.warning("No ThunderBorg found, check you are attached :)")
    else:
        logging.warning(
            "No ThunderBorg at address %02X, but we did find boards:" % (i2cAddress)
        )
        for board in boards:
            logging.info("%02X (%d)" % (board, board))
        logging.info(
            "If you need to change the I2C address change the setup line so it is correct, e.g."
        )
        logging.info("TB.i2cAddress = 0x%02X" % (boards[0]))
    sys.exit()

TB.SetCommsFailsafe(False)  # Disable the communications failsafe

# initialise mpu6050 thread
mpu = MPU6050()
mpu.setName("MPU6050")
mpu.start()

# initialise ultrasonic object
hcsr = HCSR04(
    trigger=12, echo=24, echo_timeout_ns=3000000000
)  # timeout 3 seconds (in nanoseconds)


def main(TB, mpu):
    # Power settings
    VOLTAGE_IN = 12.0  # Total battery voltage to the ThunderBorg

    # NOTE: limiter has lower bound to power motors, ~0.4 experimental lower bound
    LIMITER = 0.95  # utilise only <limiter>% of power, to slow down actions

    VOLTAGE_OUT = (
        12.0 * LIMITER
    )  # Maximum motor voltage, we limit it to 95% to allow the RPi to get uninterrupted power

    # Setup the power limits
    if VOLTAGE_OUT > VOLTAGE_IN:
        max_power = 1.0
    else:
        max_power = VOLTAGE_OUT / float(VOLTAGE_IN)

    #input_matrix = [
    #    [0, -1, 0, 0, 0],
    #    [0, -1, 0, 0, 0],
    #    [0, -1, 0, 0, 0],
    #    [0, -1, 0, 0, 0],
    #    [0, 0, 0, 0, 0],
    #    [0, 0, 0, 0, 0],
    #]

    unit_size = 1.5
    input_matrix = [
        [0,]*5,
        [0,]*5,
        [0,]*5,
        [0,]*5,
        [0,]*5,
        [0,]*5,
        [0,]*5,
        [0,]*5,
        [0,]*5,
    ]

    s_current = "x2y6"  # start at (3,0)
    s_queue = ["x0y4", "x3y0"]    # navigate to (0,0), then return to (3,0)

    #s_current = navigate(input_matrix, s_current, "x0y4", TB, mpu, unit_size, max_power)
    #s_current = navigate(input_matrix, s_current, "x3y0", TB, mpu, unit_size, max_power)

    for s_goal in s_queue:
        s_current = navigate(input_matrix, s_current, s_goal, TB, mpu, unit_size, max_power)


def navigate(input_matrix, s_start, s_goal, TB, mpu, unit_size, max_power):    
    graph = Grid(len(input_matrix), len(input_matrix[0]))
    d_star_lite = D_Star_Lite()

    logging.info("Created D* and Grid")

    graph.cells = input_matrix

    logging.info("Initialised environment:")
    
    goal_coords = d_star_lite.stateNameToCoords(s_goal)
    graph.setStart(s_start)
    graph.setGoal(s_goal)

    logging.info(f"Start: {s_start}, Goal: {s_goal}")

    k_m = 0
    s_last = s_start
    queue = []
    graph, queue, k_m = d_star_lite.initDStarLite(graph, queue, s_start, s_goal, k_m)
    s_current = s_start
    pos_coords = d_star_lite.stateNameToCoords(s_current)
    d_star_lite.updateObsticles(graph, queue, s_current, k_m, 20)
    curr_angle = 0
    s_new = None
    logging.info("Initialised D*")

    d_star_lite.computeShortestPath(graph, queue, s_current, k_m)
    graph.printGrid(s_start, s_goal, s_current)
    logging.info("Found initial shortest path")

    while s_new != s_goal:
        s_new, x_, y_, distance, curr_angle = scan_next(max_power, graph, d_star_lite, s_current, curr_angle)

        # logical bounds checking
        if distance < 40 and distance != -1:
            s_new = s_current
            graph.cells[y_][x_] = -2
            d_star_lite.updateObsticles(graph, queue, s_current, k_m, 20)
            logging.info(f"Found obstacle at {x_},{y_}")

        else:
            logging.info(f"Moving to {x_}, {y_}")
            time.sleep(0.5)
            perform_drive(unit_size, TB, mpu, max_power)
            s_current = s_new  # update current position with new position
            
        graph.printGrid(s_start, s_goal, s_current)
        # position of these two lines will need testing
        k_m += d_star_lite.heuristic_from_s(graph, s_last, s_new)
        d_star_lite.computeShortestPath(graph, queue, s_current, k_m)
        d_star_lite.updateObsticles(graph, queue, s_current, k_m, 20)
        print(s_current)

    # once reached goal, align self to 0 degrees (map North)
    perform_spin(curr_angle, 0, TB, mpu, max_power)

    logging.info("Found goal!")

    return s_current


def smallestAngle(currentAngle, targetAngle):
    # Subtract the angles, constraining the value to [0, 360)
    diff = ( targetAngle - currentAngle) % 360

    # If we are more than 180 we're taking the long way around.
    # Let's instead go in the shorter, negative direction
    if diff > 180 :
        diff = -(360 - diff)

    return diff


def scan_next(max_power, graph, d_star_lite, s_current, curr_angle):
    next_location = d_star_lite.nextInShortestPath(graph, s_current)
    current = d_star_lite.stateNameToCoords(s_current)
    next = d_star_lite.stateNameToCoords(next_location)

    logging.info(f"Next in shortest path: {next}")

    x, y = (current[0], current[1])
    x_, y_ = (next[0], next[1])

    unit_target_vector = (x_ - x, y - y_)
    target_angle = calculate_angle(unit_target_vector)

    #delta_angle = target_angle - mpu.orientation   # perform spin based on exact angle
    #delta_angle = target_angle - curr_angle # perform spin based on approx angle
    delta_angle = smallestAngle(curr_angle, target_angle)
    
    logging.info(
        f"Rotating approx {delta_angle} degrees from {mpu.orientation} degrees"
    )
    print("Facing " + str(target_angle) + " || Turn " + str(delta_angle))
 
    time.sleep(0.2)
    print(delta_angle)
    
    if delta_angle != 0:
        perform_spin(delta_angle, target_angle, TB, mpu, max_power)

    avg_distance, confidence = hcsr.get_distance()

    logging.info(
        f"Average distance of {avg_distance}cm, confidence of {confidence}"
    )

    return next_location, x_, y_, avg_distance, target_angle


def door_state_closed():
    """ Assumes agent is oriented to face door, with door being inside next cell. """
    
    avg_distance, confidence = hcsr.get_distance()

    logging.info(
        f"Average distance of {avg_distance}cm, confidence of {confidence}"
    )

    if avg_distance < 40:   # if obstable, then door closed
        return True
    else:   # no obstacle, door open
        return False


if __name__ == "__main__":
    # enable info logging
    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)

    try:
        main(TB, mpu)

    except:
        pass

    finally:
        # stop motors
        TB.SetCommsFailsafe(False)
        TB.SetLeds(0, 0, 0)
        TB.MotorsOff()

        # end sensor thread
        mpu.join()

        # exit program
        logging.info("Stopped")
        sys.exit()
