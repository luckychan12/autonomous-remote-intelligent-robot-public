# create a singleton sensor class to house gyroscope instance and provide data as thread
import board
import adafruit_mpu6050
from threading import Thread
import time

class MPU6050(Thread):
    def __init__(self):
        Thread.__init__(self)

        # initialise gyroscope board
        i2c = board.I2C()  # uses board.SCL and board.SDA
        self.mpu = adafruit_mpu6050.MPU6050(i2c)
    
        self.gyro = None
        self.acceleration = None

        self.poll = 0.01 # poll every <self.poll> seconds

    def run(self):
        while True:
            self.gyro = self.mpu.gyro
            self.acceleration = self.mpu.acceleration

            time.sleep(self.poll)

if __name__ == "__main__":
    # initialise mpu6050 board
    mpu = MPU6050()
    mpu.setName('MPU6050')
    mpu.start()

    while True:
        print(f"accelerometer: {mpu.acceleration}\ngyro: {mpu.gyro}")