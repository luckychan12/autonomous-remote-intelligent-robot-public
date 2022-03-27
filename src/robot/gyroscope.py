"""
Rotate given angle, tracked using gyroscope.
"""

import ThunderBorg3 as ThunderBorg # conversion for python 3
import time
import math
import sys

import board
import adafruit_mpu6050


# Function to spin an angle in degrees
def PerformSpin(degrees):
    if degrees < 0.0:
        # Left turn
        driveLeft = -1.0
        driveRight = +1.0
        degrees *= -1
    else:
        # Right turn
        driveLeft = +1.0
        driveRight = -1.0

    # Set the motors running
    TB.SetMotor1(driveRight * maxPower)
    TB.SetMotor2(driveLeft * maxPower)
    
    # poll the gyroscope for rotation
    # NOTE: sampling limited by real-time clock on system (0.1ms theoretical minimum, but experimentally encountered errors)
    sampling = 0.08 # poll every <sampling> seconds, fine tune to minimise overshooting target rotation
    total_rotation = 0

    while True:
        x, y, z = mpu.gyro
        x, y, z = math.degrees(x), math.degrees(y), math.degrees(z)
        abs_z = abs(z)
        sample = abs_z * sampling

        #print("Gyro X:%.2f, Y: %.2f, Z: %.2f rad/s" % (x, y, z))        
        print("Gyro: X:%.2f, Y: %.2f, Z: %.2f deg/s \t sample:%.2f \t total:%.2f" % (x, y, z, sample, total_rotation))
        #print(total_rotation)

        # NOTE: z-axis experimentally defined as 2d plane orientation
        total_rotation += sample # increment degree rotation by current rotation velocity, divided by sampling time

        # if exceeded target exit
        if total_rotation >= degrees:
            break   # exit once achieved target rotation
        # if predicted to exceed during sleep, sleep for predicted time to target, then exit
        elif (total_rotation + sample) >= degrees:
            # total degrees left in rotation (degress-total_rotation) divided by abs(z) (positive rotational velocity) gives time to sleep (in seconds) before reaching target
            sleep = (degrees-total_rotation)/abs_z

            print("Assuming constant rotation of Z:%.2f, sleeping for %.2f seconds to rotate %.2f degrees" % (abs_z, sleep, (degrees-total_rotation)))
            time.sleep(sleep)

            # NOTE: this will set total rotation to target, which is only correct assuming rotation halts immediately and rotational velocity remains constant
            # in non-demo system current orientation should be independently tracked, not adjusted using this approximation
            total_rotation += abs_z * sleep  # update final rotation for tracking
            break

        time.sleep(sampling)

    # Turn the motors off
    TB.MotorsOff()

    print(f"total rotation: {total_rotation}")

if __name__ == "__main__":
    # Setup the ThunderBorg
    TB = ThunderBorg.ThunderBorg()
    # TB.i2cAddress = 0x15                  # Uncomment and change the value if you have changed the board address
    TB.Init()
    if not TB.foundChip:
        boards = ThunderBorg.ScanForThunderBorg()
        if len(boards) == 0:
            print("No ThunderBorg found, check you are attached :)")
        else:
            print(
                "No ThunderBorg at address %02X, but we did find boards:" % (TB.i2cAddress)
            )
            for board in boards:
                print("    %02X (%d)" % (board, board))
            print(
                "If you need to change the I2C address change the setup line so it is correct, e.g."
            )
            print("TB.i2cAddress = 0x%02X" % (boards[0]))
        sys.exit()
    TB.SetCommsFailsafe(False)  # Disable the communications failsafe

    # Power settings
    voltageIn = 9.6   # Total battery voltage to the ThunderBorg

    # NOTE: limiter has lower bound to power motors, ~0.4 experimental lower bound
    limiter = 0.6     # utilise only <limiter>% of power, to slow down actions

    voltageOut = (
        12.0 * limiter
    )  # Maximum motor voltage, we limit it to 95% to allow the RPi to get uninterrupted power

    # Setup the power limits
    if voltageOut > voltageIn:
        maxPower = 1.0
    else:
        maxPower = voltageOut / float(voltageIn)

    # initialise gyroscope board
    i2c = board.I2C()  # uses board.SCL and board.SDA
    mpu = adafruit_mpu6050.MPU6050(i2c)

    PerformSpin(90)