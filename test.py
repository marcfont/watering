from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time
from time import sleep
import threading
import json
import requests

def mc_get_max_temperatures():
    # https://3.python-requests.org/
    # todo: implement

    try:
        r = requests.get('https://api.meteo.cat/xema/v1/variables/estadistics/diaris/1001?codiEstacio=UG&any=2013&mes=12')

        # View response data.
        print(r.json())

    except ConnectionError:
        print('ConnectionError')
    except requests.exceptions.RequestException:
        print('requests.exceptions.RequestException')


def compute_watering_minutes():
    print("I am compute_watering_minutes: ")

    global minutes
    minutes = [11, 22, 33]

    print(minutes)


def enable(valve_id):
    print("Enable valve num: " + str(valve_id))


def disable(valve_id):
    print("Disable valve num: " + str(valve_id))
    result_available.set()


if __name__ == '__main__':
    background_scheduler = BackgroundScheduler()
    background_scheduler.start()
    not_scheduled = True

    result_available = threading.Event()

    minutes = None

    LEFT_CIRCUIT = 0
    FAR_CIRCUIT = 1
    RIGHT_CIRCUIT = 2
    CIRCUITS = [LEFT_CIRCUIT, FAR_CIRCUIT, RIGHT_CIRCUIT]

    START_TIME = time(12, 0, 0)
    DELAY_BETWEEN_CIRCUITS = time(00, 00, 5)

    now = datetime.now().replace(hour=START_TIME.hour, minute=START_TIME.minute, second=START_TIME.second)

    print(now)

    # runs once a day at hour:minute:second
    background_scheduler.add_job(compute_watering_minutes, 'cron', hour=now.hour, minute=now.minute, second=now.second,
                                 max_instances=1)

    while True:
        if minutes:
            for i in CIRCUITS:
                deadline = datetime.now()

                if minutes[i] > 0:
                    # Start watering cycle for i-th circuit
                    enable(i)

                    # TODO: canviar a minuts i no segons
                    # deadline.replace(second=deadline.minute + minutes[i])
                    deadline.replace(second=deadline.second + minutes[i])
                    background_scheduler.add_job(disable, 'date', run_date=deadline, args=[i], id='disable'+str(i))
                    result_available.wait()

                    print("now sleeping...")
                    sleep(DELAY_BETWEEN_CIRCUITS.second)

                    # for i = 1 to 3
                    # enable i
                    # schedule a date triggered job to run disable(i) at now + minutes[i]
                    # sleep for DELAY_BETWEEN_CIRCUITS seconds

            print("For loop finished")
            minutes = None
