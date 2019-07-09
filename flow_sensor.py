import time
import datetime
import RPi.GPIO as GPIO

global count
count = 0


def sensor_callback(channel):
    # Called if sensor output changes
    global count
    count = count + 1
    timestamp = time.time()
    stamp = datetime.datetime.now().strftime("%H:%M:%S.%f")
    if GPIO.input(channel):
        # No magnet
        print("Sensor HIGH " + stamp)
    else:
        # Magnet
        print("Sensor LOW " + stamp)

def main():
    # Wrap main content in a try block so we can
    # catch the user pressing CTRL-C and run the
    # GPIO cleanup function. This will also prevent
    # the user seeing lots of unnecessary error
    # messages.

    try:
        # Loop until users quits with CTRL-C
        while True:
            time.sleep(0.00000000001)

    except KeyboardInterrupt:
        # Reset GPIO settings
        GPIO.cleanup()


GPIO.setmode(GPIO.BOARD)

print("Setup GPIO pin as input on GPIO2")

# Set Switch GPIO as input
# Pull high by default
GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(13, GPIO.RISING, callback=sensor_callback)

if __name__ == "__main__":
    main()
