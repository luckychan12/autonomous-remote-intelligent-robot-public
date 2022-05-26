from math import dist
import RPi.GPIO as GPIO
import time
import logging

class HCSR04:
    def __init__(self, trigger, echo, echo_timeout_ns):
        self.trigger = trigger
        self.echo = echo
        self.echo_timeout_ns = echo_timeout_ns

        GPIO.setmode(GPIO.BCM)
        logging.debug("setmode")
        
        GPIO.setup(self.trigger, GPIO.OUT)
        logging.debug("setup trigger")
        GPIO.setup(self.echo, GPIO.IN)
        logging.debug("setup echo")
        GPIO.output(self.trigger, False)
        logging.debug("set trigger to False")
        time.sleep(2)   # settle sensor
        logging.debug("settled sensor")

    def pulse(self):
        logging.debug("pulsing")

        # NOTE: no debugging during pulse below, as messes up timings
        GPIO.output(self.trigger, True) # send pulse for 0.00001 seconds
        time.sleep(0.001)
        GPIO.output(self.trigger, False)

        pulse_sent = time.time_ns()

        pulse_start_ns = time.time_ns() # preset in case of instant exit from while loop
        while GPIO.input(self.echo) == 0:   # wait for response
            pulse_start_ns = time.time_ns()   # record time when response is recieved

            if pulse_start_ns - pulse_sent > self.echo_timeout_ns: # if waited too long, exit
                logging.debug("pulse timeout")
                return -1

        pulse_end_ns = time.time_ns() # preset in case of instant exit from while loop
        while GPIO.input(self.echo) == 1:   # wait for pulse to end
            pulse_end_ns = time.time_ns() # record pulse end time

            if (pulse_start_ns - pulse_sent) + (pulse_end_ns - pulse_start_ns) > self.echo_timeout_ns:  # if time between pulse send and pulse end is greater than timeout
                logging.debug("pulse end timeout")
                return -1
        
        # NOTE: debug from here
        logging.debug(f"pulse start: {pulse_start_ns}")
        logging.debug(f"pulse end: {pulse_end_ns}")

        pulse_duration = (pulse_end_ns - pulse_start_ns) / 1000000000   # convert from nanoseconds to seconds
        logging.debug(f"pulse duration: {pulse_duration}")
        distance = pulse_duration * 17150   # calculate distance using speed of sound (in cm/s)

        return distance

    def cleanup(self):
        GPIO.cleanup()  # reset pins
        logging.debug("cleaned up pins")

if __name__ == "__main__":
    # enable debug logging
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

    sensor = HCSR04(trigger=12, echo=24)
    try:
        while 1:
            distance = sensor.pulse()
            distance = round(distance, 3)

            # logical bounds checking
            if distance > 400 or distance < 0:   # 400cm sensor range, also return error for timeouts
                distance = f"ERROR ({distance})"    # log as sensor error

            logging.info(f"Distance: {distance}cm")
            time.sleep(0.1)
    except KeyboardInterrupt:
        sensor.cleanup()
    
    sensor.cleanup()    # remember to perform manual cleanup