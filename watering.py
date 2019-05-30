from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time, timedelta
from time import sleep
import threading
import json
import requests
import urllib3
import statistics
from datetime import date
# no need to worry about SSL to verify connection to meteo.cat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADER = {'x-api-key': 'yTLyU2J2XraoSZ4LEHpG35izWgS22AMs1DmRJqmZ'}


LEFT_CIRCUIT = 0
FAR_CIRCUIT = 1
RIGHT_CIRCUIT = 2
CIRCUITS = [LEFT_CIRCUIT, FAR_CIRCUIT, RIGHT_CIRCUIT]

START_TIME = time(17, 50, 25)
DELAY_BETWEEN_CIRCUITS = time(00, 00, 5)


def meteocat_api_request(api_date, param):
    """
    day(date), day to get the data from
    param(String):
    temp-->32 returns [max, min]
    rain-->35 returns [sum()]
    rh-->33 returns [max, min]
    rad->36 returns [calculation()], see readme.md
    wind->30 returns [mean()]
    """
    operations = {'temp': '32', 'rain': '35', 'rh': '33', 'rad': '36', 'wind': '30'}

    if type(api_date) is not date:
        raise TypeError('First parameter must be datetime.dat, not %s' % type(api_date))
    if not operations.__contains__(param):
        raise TypeError('Second parameter has unaccepted value %s' % param)

    try:
        # url model --> https://api.meteo.cat/xema/v1/variables/mesurades/36/2019/05/28?codiEstacio=CC
        url = 'https://api.meteo.cat/xema/v1/variables/mesurades/' + str(operations[param]) + '/' + str(api_date.year) \
              + '/' + str(api_date.month).zfill(2) + '/'+str(api_date.day).zfill(2) + '?codiEstacio=CC'
        r = requests.get(url, headers=HEADER, verify=False)

        # sample:
        # {'codi': 35, 'lectures':
        # [{'data': '2019-05-03T00:00Z', 'valor': 0.5, 'estat': 'V', 'baseHoraria': 'SH'},
        # {'data': '2019-05-03T00:30Z', 'valor': 0, 'estat': 'V', 'baseHoraria': 'SH'}]}
        #
        # dt = datetime.strptime('2019-05-03T00:00Z', '%Y-%m-%dT%H:%MZ')
        if r.ok:
            data = json.loads(r.text)
            values = []

            print(data)

            for d in data["lectures"]:
                values.append(d["valor"])

            if param == 'temp' or param == 'rh':
                return [max(values), min(values)]
            elif param == 'rain':
                return sum(values)
            elif param == 'rad':
                # Irradiació = (average(irradiància) * segons en el període) / 1000000
                return statistics.mean(values) * 60 * 30 * len(values) / 1000000
            elif param == 'wind':
                return statistics.mean(values)
        else:
            # todo: error handling
            print(r)

    except ConnectionError as ex:
        print('Exception thrown: ConnectionError')
        print(ex)
    except requests.exceptions.RequestException as ex:
        print('Exception thrown: requests.exceptions.RequestException')
        print(ex)


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
