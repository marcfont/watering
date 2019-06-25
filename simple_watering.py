from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time, timedelta
import threading
import urllib3

# import RPi.GPIO as GPIO

# no need to worry about SSL to verify connection to meteo.cat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADER = {'x-api-key': 'yTLyU2J2XraoSZ4LEHpG35izWgS22AMs1DmRJqmZ'}

# GPIO.setmode(GPIO.BOARD)  #Board GPIO Pin numbers

GPIO4_RIGHT = 16
GPIO5_FAR = 18
GPIO6_LEFT = 22

CIRCUITS = [GPIO4_RIGHT, GPIO5_FAR, GPIO6_LEFT]


def enable_valve(valve_id):
    print('enable thread id: ' + str(threading.get_ident()))
    print("Enable valve num: " + str(valve_id))
    print("Now watering........")

    # GPIO.output(valve_id, GPIO.HIGH)


def disable_valve(valve_id):
    print('disable thread id: ' + str(threading.get_ident()))
    print("..............and watering stops")
    print("Disable valve num: " + str(valve_id))

    # GPIO.output(valve_id, GPIO.LOW)

    global result_available
    result_available.set()


# def gpio_init():
#     GPIO.setmode(GPIO.BOARD)
#
#     GPIO.setup(GPIO2_FLOW_METER, GPIO.IN)
#     GPIO.setup(GPIO4_RIGHT, GPIO.OUT)
#     GPIO.setup(GPIO5_FAR, GPIO.OUT)
#     GPIO.setup(GPIO6_LEFT, GPIO.OUT)
#
#     # this shouldn't be needed but here it comes just in case
#     GPIO.output(GPIO4_RIGHT, GPIO.LOW)
#     GPIO.output(GPIO5_FAR, GPIO.LOW)
#     GPIO.output(GPIO6_LEFT, GPIO.LOW)


if __name__ == '__main__':
    # gpio_init()

    background_scheduler = BackgroundScheduler()
    background_scheduler.start()
    not_scheduled = True

    START_TIME_MORNING = time(6, 0, 0)
    START_TIME_NIGHT = time(22, 0, 0)

    MINUTES_MORNING = [20, 5, 20]
    MINUTES_NIGHT = [5, 1, 5]

    morning_run = datetime.now().replace(hour=START_TIME_MORNING.hour, minute=START_TIME_MORNING.minute,
                                         second=START_TIME_MORNING.second)
    night_run = datetime.now().replace(hour=START_TIME_NIGHT.hour, minute=START_TIME_NIGHT.minute,
                                       second=START_TIME_NIGHT.second)

    for i in range(0, len(CIRCUITS)):
        # run once a day at START_TIME_MORNING + 1 second for MINUTES_MORNING[i] minutes
        morning_run = morning_run + timedelta(seconds=1)
        background_scheduler.add_job(enable_valve, 'cron', hour=morning_run.hour, minute=morning_run.minute,
                                     second=morning_run.second, max_instances=1, args=[CIRCUITS[i]])

        morning_run = morning_run + timedelta(minutes=MINUTES_MORNING[i], seconds=1)
        background_scheduler.add_job(disable_valve, 'cron', hour=morning_run.hour, minute=morning_run.minute,
                                     second=morning_run.second, max_instances=1, args=[CIRCUITS[i]])

        # run once a day at START_TIME_NIGHT + 1 second for MINUTES_NIGHT[i] minutes
        night_run = night_run + timedelta(seconds=1)
        background_scheduler.add_job(enable_valve, 'cron', hour=night_run.hour, minute=night_run.minute,
                                     second=night_run.second, max_instances=1, args=[CIRCUITS[i]])

        night_run = night_run + timedelta(minutes=MINUTES_NIGHT[i], seconds=1)
        background_scheduler.add_job(disable_valve, 'cron', hour=night_run.hour, minute=night_run.minute,
                                     second=night_run.second, max_instances=1, args=[CIRCUITS[i]])

    print(background_scheduler.print_jobs())

    while True:
        pass
