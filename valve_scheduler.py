from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import time
import logging
import smtplib
import requests
import ssl
import json
import statistics
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import RPi.GPIO as GPIO
import math
import urllib3
# no need to worry about SSL to verify connection to meteo.cat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADER = {'x-api-key': 'yTLyU2J2XraoSZ4LEHpG35izWgS22AMs1DmRJqmZ'}


GPIO_2_FLOW_METER = 13
GPIO_4_RIGHT = 16
GPIO_5_FAR = 18
GPIO_6_LEFT = 22

CIRCUITS = [GPIO_4_RIGHT, GPIO_5_FAR, GPIO_6_LEFT]
CIRCUIT_NAMES = dict([(GPIO_4_RIGHT, 'Right circuit'), (GPIO_5_FAR, 'Far circuit'), (GPIO_6_LEFT, 'Left circuit')])
DELAY_BETWEEN_CIRCUITS = 5

START_TIME_MORNING = datetime.time(6, 0, 0)
START_TIME_NIGHT = datetime.time(22, 0, 0)

flow_rising_count = 0
real_start_time_s = None


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

    if type(api_date) is not datetime.date:
        raise TypeError('First parameter must be datetime.dat, not %s' % type(api_date))
    if not operations.__contains__(operation_id):
        raise TypeError('Second parameter has unaccepted value %s' % operation_id)

    try:
        # url model --> https://api.meteo.cat/xema/v1/variables/mesurades/36/2019/05/28?codiEstacio=CC
        url = 'https://api.meteo.cat/xema/v1/variables/mesurades/' + str(operations[operation_id]) + '/' + \
              str(api_date.year) + '/' + str(api_date.month).zfill(2) + '/' \
              + str(api_date.day).zfill(2) + '?codiEstacio=CC'
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
            logging.error('ERROR #1 in __meteocat_api_request')

    except ConnectionError as ex:
        print('Exception thrown: ConnectionError')
        logging.error('ERROR #1 in __meteocat_api_request', ex)
    except requests.exceptions.RequestException as ex:
        print('Exception thrown: requests.exceptions.RequestException')
        logging.error('ERROR #2 in __meteocat_api_request', ex)

def print_evapotranspiration_rain_particular_days():
    """
    evapotranspiration calculation using meteo.cat api queries and FAO formula (see readme)
    :param start_day: 0 means we start calculating from today, 1 from yesterday and so on
    :param num_days: number of days to add up in the calculation. Must be positive number.
    :return: [evapotranspiration, rain (mm)]
    """

    when = datetime.date.today()

    #for j in range(, 11):
    when = when.replace(2019, 7, 10)
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

    print(str(when), et0, rain)


def evapotranspiration_rain_day(start_day, num_days):
    """
    evapotranspiration calculation using meteo.cat api queries and FAO formula (see readme)
    :param start_day: 0 means we start calculating from today, 1 from yesterday and so on
    :param num_days: number of days to add up in the calculation. Must be positive number.
    :return: [evapotranspiration, rain (mm)]
    """
    if type(num_days) is not int:
        raise TypeError('First parameter must be int, not %s' % type(num_days))
    if num_days <= 0:
        raise TypeError('num_days <= 0 --> value %s' % eval(num_days))

    et0_out = rain_out = 0

    for j in range(num_days):
        when = datetime.date.today() - datetime.timedelta(days=start_day+j)

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

    return [round(et0_out, 1), round(rain_out, 1)]


def minutes(start_day, num_days):
    KJ = 0.6
    EFFECTIVE_RAIN = 0.8
    REAL_ETO_TO_MINUTES_SLOPE = 14
    STRAWBERRY_TO_GRASS = 1/8
    NIGHT_PORTION = 1/5
    MORNING_PORTION = 4/5
    MIN_ETO_REAL = 0.6 # Això són 8.4 minuts de gespa i 1.1 de maduixes

    [eto, rain] = evapotranspiration_rain_day(start_day, num_days)
    eto_real = eto * KJ - rain * EFFECTIVE_RAIN

    if eto_real >= MIN_ETO_REAL:
        grass_minutes = eto_real * REAL_ETO_TO_MINUTES_SLOPE
        strawberry_minutes = grass_minutes * STRAWBERRY_TO_GRASS

        morning = [round(grass_minutes * MORNING_PORTION / 2), round(strawberry_minutes * MORNING_PORTION),
                   round(grass_minutes * MORNING_PORTION / 2)]
        night = [round(grass_minutes * NIGHT_PORTION / 2), round(strawberry_minutes * NIGHT_PORTION),
                 round(grass_minutes * NIGHT_PORTION / 2)]

        return [morning, night]
    else:
        return [[0, 0, 0], [0, 0, 0]]

def send_email(subject, body):
    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    sender_email = "watering.espona@gmail.com"  # Enter your address
    receiver_email = "marc.font@gmail.com"  # Enter receiver address
    password = "BeWaterMyFriend"

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))
    text = message.as_string()

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, text)


def enable_valve(valve_id):
    logging.info("Enable valve in pin: " + str(valve_id))
    send_email("Enable", str(CIRCUIT_NAMES[valve_id]) + " has been enabled.")

    global real_start_time_s
    real_start_time_s = datetime.now()
    GPIO.output(valve_id, GPIO.LOW)
    GPIO.add_event_detect(GPIO_2_FLOW_METER, GPIO.RISING, callback=sensor_callback)


def disable_valve(valve_id):
    GPIO.output(valve_id, GPIO.HIGH)
    GPIO.remove_event_detect(GPIO_2_FLOW_METER)

    global real_start_time_s
    real_stop_time_s = datetime.now()
    delta = real_stop_time_s - real_start_time_s
    pouring_time_s = delta.seconds
    logging.info('pouring_time_s', pouring_time_s)

    global flow_rising_count
    flow_l_per_minute = (flow_rising_count / pouring_time_s) / 4.8
    logging.info('flow_rising_count', flow_rising_count)
    logging.info('flow_l_per_minute', flow_l_per_minute)
    volume = flow_l_per_minute * (pouring_time_s / 60)
    logging.info('volume', volume)

    flow_rising_count = 0

    send_email("Disable", str(CIRCUIT_NAMES[valve_id]) + " has been disabled.\nWatering volume has been "
               + str(round(volume)) + " liters.")

    logging.info("Disable valve in pin: " + str(valve_id))
    logging.info("Watering volume has been " + str(round(volume)) + " liters")


def sensor_callback(channel):
    global flow_rising_count
    flow_rising_count = flow_rising_count + 1


def gpio_init():
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)

    GPIO.setup(GPIO_2_FLOW_METER, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    GPIO.setup(GPIO_4_RIGHT, GPIO.OUT)
    GPIO.setup(GPIO_5_FAR, GPIO.OUT)
    GPIO.setup(GPIO_6_LEFT, GPIO.OUT)

    # this shouldn't be needed but here it comes just in case
    GPIO.output(GPIO_4_RIGHT, GPIO.HIGH)
    GPIO.output(GPIO_5_FAR, GPIO.HIGH)
    GPIO.output(GPIO_6_LEFT, GPIO.HIGH)


def schedule_morning_run(run_time):
    # Morning run takes into account today and yesterday
    [minutes_morning, dummy] = minutes(0, 2)

    send_email("Watering morning run scheduled: ",
               'START_TIME_MORNING: ' + datetime.now().strftime("%H:%M:%S") + '\n' +
               'MINUTES_MORNING: ' + str(minutes_morning))

    if minutes_morning != [0, 0, 0]:
        for i in range(0, len(CIRCUITS)):
            run_time = run_time + datetime.timedelta(seconds=DELAY_BETWEEN_CIRCUITS)
            background_scheduler.add_job(enable_valve, 'date', run_date=run_time, args=[CIRCUITS[i]])

            run_time = run_time + datetime.timedelta(minutes=minutes_morning[i], seconds=DELAY_BETWEEN_CIRCUITS)
            background_scheduler.add_job(disable_valve, 'date', run_date=run_time, args=[CIRCUITS[i]])


def schedule_night_run (run_time):
    # Night run takes into account just today
    [dummy, minutes_night] = minutes(0, 1)

    send_email("Watering night run scheduled: ",
               'START_TIME_NIGHT: ' + datetime.now().strftime("%H:%M:%S") + '\n' +
               'MINUTES_NIGHT: ' + str(minutes_night))

    if minutes_night != [0, 0, 0]:
        for i in range(0, len(CIRCUITS)):
            run_time = run_time + datetime.timedelta(seconds=DELAY_BETWEEN_CIRCUITS)
            background_scheduler.add_job(enable_valve, 'date', run_date=run_time, args=[CIRCUITS[i]])

            run_time = run_time + datetime.timedelta(minutes=minutes_night[i], seconds=DELAY_BETWEEN_CIRCUITS)
            background_scheduler.add_job(disable_valve, 'date', run_date=run_time, args=[CIRCUITS[i]])


if __name__ == '__main__':
    try:
        logging.basicConfig(filename='simple_watering.log', level=logging.INFO)
        logging.info('------------------------------------------------------------')
        logging.info('------------------------System boot on: ' + datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))
        logging.info('------------------------------------------------------------')

        background_scheduler = BackgroundScheduler()
        background_scheduler.start()

        gpio_init()

        morning_run = datetime.now().replace(hour=START_TIME_MORNING.hour, minute=START_TIME_MORNING.minute,
                                             second=START_TIME_MORNING.second)
        night_run = datetime.now().replace(hour=START_TIME_NIGHT.hour, minute=START_TIME_NIGHT.minute,
                                           second=START_TIME_NIGHT.second)

        background_scheduler.add_job(schedule_morning_run, 'cron', hour=morning_run.hour, minute=morning_run.minute,
                                     second=morning_run.second, max_instances=1, args=[morning_run])
        background_scheduler.add_job(schedule_night_run, 'cron', hour=night_run.hour, minute=night_run.minute,
                                     second=night_run.second, max_instances=1, args=[night_run])

        send_email("Watering calculation scheduled (program restart)",
                   'START_TIME_MORNING: ' + str(START_TIME_MORNING) + '\n' +
                   'START_TIME_NIGHT: ' + str(START_TIME_NIGHT))

        while True:
            time.sleep(1000)

    except Exception as error:
        logging.error('Error in __main__: ' + repr(error))
        send_email("Genaral failure", 'Error in __main__: ' + repr(error))
