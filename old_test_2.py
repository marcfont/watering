from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time, timedelta
from time import sleep
import threading
import json
import requests
import urllib3
import statistics
from datetime import date
import math
import RPi.GPIO as GPIO
# no need to worry about SSL to verify connection to meteo.cat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADER = {'x-api-key': 'yTLyU2J2XraoSZ4LEHpG35izWgS22AMs1DmRJqmZ'}

GPIO.setmode(GPIO.BOARD)  #Board GPIO Pin numbers
GPIO2_FLOW_METER = 13
GPIO4_RIGHT = 16
GPIO5_FAR = 18
GPIO6_LEFT = 22

CIRCUITS = [GPIO4_RIGHT, GPIO5_FAR, GPIO6_LEFT]

START_TIME = time(16, 0, 0)
DELAY_BETWEEN_CIRCUITS = time(00, 00, 5)


def __meteocat_api_request(api_date, operation_id):
    """
    :param api_date: day to get the data from
    :param operation_id: allowed values: 'temp', 'rain', 'rh', 'rad', 'wind'
    temp-->32 returns [max, min]
    rain-->35 returns [sum()]
    rh-->33 returns [max, min]
    rad->36 returns [calculation()], see readme.md
    wind->30 returns [mean()]
    """
    operations = {'temp': '32', 'rain': '35', 'rh': '33', 'rad': '36', 'wind': '30'}

    if type(api_date) is not date:
        raise TypeError('First parameter must be datetime.dat, not %s' % type(api_date))
    if not operations.__contains__(operation_id):
        raise TypeError('Second parameter has unaccepted value %s' % operation_id)

    try:
        # url model --> https://api.meteo.cat/xema/v1/variables/mesurades/36/2019/05/28?codiEstacio=CC
        url = 'https://api.meteo.cat/xema/v1/variables/mesurades/' + str(operations[operation_id]) + '/' + str(api_date.year) \
              + '/' + str(api_date.month).zfill(2) + '/' + str(api_date.day).zfill(2) + '?codiEstacio=CC'
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

            for d in data["lectures"]:
                values.append(d["valor"])

            if operation_id == 'temp' or operation_id == 'rh':
                return [max(values), min(values)]
            elif operation_id == 'rain':
                return sum(values)
            elif operation_id == 'rad':
                # Irradiació = (average(irradiància) * segons en el període) / 1000000
                return statistics.mean(values) * 60 * 30 * len(values) / 1000000
            elif operation_id == 'wind':
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


def evapotranspiration_rain_day(num_days):
    """
    evapotranspiration calculation using meteo.cat api queries and FAO formula (see readme)
    :param num_days: number of days to take into account for the calculation. Must be positive number. 1 means today,
    2 means today and yesterday, and so forth
    :return: [evapotranspiration, rain (mm)]
    """
    if type(num_days) is not int:
        raise TypeError('First parameter must be int, not %s' % type(num_days))
    if num_days <= 0:
        #todo: error handling
        print("error")

    et0_out = rain_out = 0

    for j in range(num_days):
        when = date.today() - timedelta(days=j)

        [t_max, t_min] = __meteocat_api_request(when, 'temp')
        rain = __meteocat_api_request(when, 'rain')
        [rh_max, rh_min] = __meteocat_api_request(when, 'rh')
        rn_g = __meteocat_api_request(when, 'rad')
        u2 = __meteocat_api_request(when, 'wind')

        t_mean = (t_max + t_min) / 2
        delta = (4098 * (0.6108 ** ((12.27 * t_mean) / (t_mean + 237.3)))) / ((t_mean + 237.3) ** 2)
        y = 0.063   # directament de la taula 2.2 i sense fer servir la eq7
        eq2 = delta / (delta + y * (1 + 0.34 * u2))
        eq3 = y / (delta + y * (1 + 0.34 * u2))
        eq4 = 900 / ((t_mean + 273) * u2)
        ea = (1.431 * (rh_max / 100) + 2.564 * (rh_min / 100)) / 2
        eot_max = 0.6108 * math.exp((17.27 * t_max) / (t_max + 237.3))
        eot_min = 0.6108 * math.exp((17.27 * t_min) / (t_min + 237.3))
        es = (eot_max + eot_min) / 2
        es_ea = es - ea
        eq5 = 0.408 * rn_g * eq2
        eq6 = eq4 * es_ea * eq3
        et0 = eq5 + eq6

        et0_out = et0_out + et0
        rain_out = rain_out + rain

    print([round(et0_out, 1), round(rain_out, 1)])
    return [round(et0_out, 1), round(rain_out, 1)]


def compute_watering_minutes():
    print("I am compute_watering_minutes: ")

    # TODO: call to evapo calculation so it computes minutes instead of manually set (last line of code)
    # evapotranspiration_rain_day(3)

    # TODO: implement code for deriving minutes from evapo, square meters, flow and so on...

    global minutes
    minutes = [20, 7, 20]

    print(minutes)


def enable(valve_id):
    print('enable thread id: ' + str(threading.get_ident()))
    print("Enable valve num: " + str(valve_id))
    print("Now watering........")
    GPIO.output(valve_id, GPIO.HIGH)


def disable(valve_id):
    print('disable thread id: ' + str(threading.get_ident()))
    print("..............and watering stops")
    print("Disable valve num: " + str(valve_id))
    GPIO.output(valve_id, GPIO.LOW)

    global result_available
    result_available.set()


def gpio_init():
    GPIO.setmode(GPIO.BOARD)

    GPIO.setup(GPIO2_FLOW_METER, GPIO.IN)
    GPIO.setup(GPIO4_RIGHT, GPIO.OUT)
    GPIO.setup(GPIO5_FAR, GPIO.OUT)
    GPIO.setup(GPIO6_LEFT, GPIO.OUT)

    # this shouldn't be needed but here it comes just in case
    GPIO.output(GPIO4_RIGHT, GPIO.LOW)
    GPIO.output(GPIO5_FAR, GPIO.LOW)
    GPIO.output(GPIO6_LEFT, GPIO.LOW)


if __name__ == '__main__':
    gpio_init()

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
                    print("Now sleeping...")
                    sleep(DELAY_BETWEEN_CIRCUITS.second)

            print("For loop finished")
            minutes = None
