from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time, timedelta
from time import sleep
import threading
import json
import requests

def mc_get_max_temperatures():
    # https://3.python-requests.org/
    # todo: implement

    try:
        payload = {'key1': 'value1', 'key2': 'value2'}
        url = 'https://api.meteo.cat/xema/v1/variables/estadistics/diaris/1001?codiEstacio=UG&any=2013&mes=12'
        r = requests.get(url, params=payload)

        # View response data.
        print(r.json())

    except ConnectionError:
        print('ConnectionError')
    except requests.exceptions.RequestException:
        print('requests.exceptions.RequestException')


def compute_watering_minutes():
    print("I am compute_watering_minutes: ")

    # TODO: to be implemented
    global minutes
    minutes = [11, 22, 33]

    print(minutes)


def enable(valve_id):
    print('enable thread id: ' + str(threading.get_ident()))
    print("Enable valve num: " + str(valve_id))
    print("Now watering........")


def disable(valve_id):
    print('disable thread id: ' + str(threading.get_ident()))
    print("..............and watering stops")
    print("Disable valve num: " + str(valve_id))
    global result_available
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

    START_TIME = time(17, 50, 25)
    DELAY_BETWEEN_CIRCUITS = time(00, 00, 5)

    now = datetime.now().replace(hour=START_TIME.hour, minute=START_TIME.minute, second=START_TIME.second)

    print('main thread id: '+str(threading.get_ident()))
    print(now)

    # runs once a day at START_TIME
    background_scheduler.add_job(compute_watering_minutes, 'cron', hour=now.hour, minute=now.minute, second=now.second,
                                 max_instances=1)

    # main loop structure:
    # if watering times have been computed and times are greater than zero
    #   enable i
    #   schedule a date triggered job to run disable(i) at now + minutes[i]
    #   sleep for DELAY_BETWEEN_CIRCUITS seconds
    while True:
        if minutes:
            for i in CIRCUITS:
                deadline = datetime.now()

                if minutes[i] > 0:
                    # Start watering cycle for i-th circuit
                    enable(i)

                    # Schedule stop watering in minutes[i]
                    # TODO: canviar a minuts i no segons
                    # deadline = deadline + timedelta(minutes=minutes[i])
                    deadline = deadline + timedelta(seconds=minutes[i])
                    background_scheduler.add_job(disable, 'date', run_date=deadline, args=[i], id='disable'+str(i))
                    # waits for disable to be executed
                    result_available.wait()
                    result_available.clear()

                    # Delays next valve opening for DELAY_BETWEEN_CIRCUITS seconds
                    print("now sleeping...")
                    sleep(DELAY_BETWEEN_CIRCUITS.second)

            print("For loop finished")
            minutes = None
