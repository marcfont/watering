from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date, time, timedelta, datetime
import time as t
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

START_TIME_MORNING = time(6, 0, 0)
START_TIME_NIGHT = time(22, 00, 0)

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

    if type(api_date) is not date:
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

            for d in data['lectures']:
                values.append(d['valor'])

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
            logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' ERROR #1 in __meteocat_api_request')

    except Exception as ex:
        logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in enable_valve: ' + repr(ex))
        send_email('General failure', 'Error in enable_valve: ' + repr(ex))
        

def evapotranspiration_rain_day(morning_night):
    """
    evapotranspiration calculation using meteo.cat api queries and FAO formula (see readme)
    :param morning_night: if 'morning' returns data from yesterday + rain from today. Returns data from today otherwise
    :return: [evapotranspiration, rain (mm)]
    """

    try:
        et0_out = rain_out = 0

        if morning_night == 'morning':
            # et0 from yesterday, rain from yesterday + today
            when = date.today()
            rain = __meteocat_api_request(when, 'rain')
            when = date.today() - timedelta(days=1)
            rain = rain + __meteocat_api_request(when, 'rain')
        elif morning_night == 'night':
            # et0 from today, rain from today
            when = date.today()
            rain = __meteocat_api_request(when, 'rain')
        else:
            logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Mongo error in evapotranspiration_rain_day')
            send_email('General failure', 'Mongo error in evapotranspiration_rain_day')

        [t_max, t_min] = __meteocat_api_request(when, 'temp')
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

    except Exception as ex:
        logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in enable_valve: ' + repr(ex))
        send_email('General failure', 'Error in enable_valve: ' + repr(ex))


def minutes(morning_night):
    try:
        KJ = 0.6
        EFFECTIVE_RAIN = 0.8
        REAL_ETO_TO_MINUTES_SLOPE = 13
        STRAWBERRY_TO_GRASS = 1/8
        NIGHT_PORTION = 1/5
        MORNING_PORTION = 4/5
        MIN_ETO_REAL = 0.6 # Això són 8.4 minuts de gespa i 1.1 de maduixes

        [eto, rain] = evapotranspiration_rain_day(morning_night)
        eto_real = eto * KJ - rain * EFFECTIVE_RAIN

        if eto_real >= MIN_ETO_REAL:
            grass_minutes = eto_real * REAL_ETO_TO_MINUTES_SLOPE
            strawberry_minutes = grass_minutes * STRAWBERRY_TO_GRASS

            if morning_night == 'morning':
                morning = [round(grass_minutes * MORNING_PORTION / 2), round(strawberry_minutes * MORNING_PORTION),
                           round(grass_minutes * MORNING_PORTION / 2)]
                return morning
            elif morning_night == 'night':
                night = [round(grass_minutes * NIGHT_PORTION / 2), round(strawberry_minutes * NIGHT_PORTION),
                         round(grass_minutes * NIGHT_PORTION / 2)]
                return night
            else:
                logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Mongo error in enable_valve')
                send_email('General failure', 'Mongo error in enable_valve')
        else:
            return [0, 0, 0]

    except Exception as ex:
        logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in enable_valve: ' + repr(ex))
        send_email('General failure', 'Error in enable_valve: ' + repr(ex))


def send_email(subject, body):
    try:
        port = 465  # For SSL
        smtp_server = 'smtp.gmail.com'
        sender_email = 'watering.espona@gmail.com'  # Enter your address
        receiver_email = 'marc.font@gmail.com'  # Enter receiver address
        password = 'BeWaterMyFriend'

        message = MIMEMultipart()
        message['From'] = sender_email
        message['To'] = receiver_email
        message['Subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        text = message.as_string()

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, text)

    except Exception as ex:
        logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in enable_valve: ' + repr(ex))
        send_email('General failure', 'Error in enable_valve: ' + repr(ex))


def enable_valve(valve_id):
    try:
        logging.info(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Enable valve in pin: ' + str(valve_id))
        send_email('Enable', str(CIRCUIT_NAMES[valve_id]) + ' has been enabled.')

        global real_start_time_s
        real_start_time_s = datetime.now()
        GPIO.output(valve_id, GPIO.LOW)
        GPIO.add_event_detect(GPIO_2_FLOW_METER, GPIO.RISING, callback=sensor_callback)

    except Exception as ex:
        logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in enable_valve: ' + repr(ex))
        send_email('General failure', 'Error in enable_valve: ' + repr(ex))


def disable_valve(valve_id):
    try:
        GPIO.output(valve_id, GPIO.HIGH)
        GPIO.remove_event_detect(GPIO_2_FLOW_METER)

        global real_start_time_s
        real_stop_time_s = datetime.now()
        delta = real_stop_time_s - real_start_time_s
        pouring_time_s = delta.seconds

        global flow_rising_count
        flow_l_per_minute = (flow_rising_count / pouring_time_s) / 4.8
        volume = flow_l_per_minute * (pouring_time_s / 60)
        flow_rising_count = 0

        send_email('Disable', str(CIRCUIT_NAMES[valve_id]) + ' has been disabled.\nWatering volume has been '
                   + str(round(volume)) + ' liters.')

        logging.info(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Disable valve in pin: ' + str(valve_id))
        logging.info(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Watering volume has been ' + str(round(volume))
                                             + ' liters')

    except Exception as ex:
        logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in disable_valve: ' + repr(ex))
        send_email('General failure', 'Error in disable_valve: ' + repr(ex))


def sensor_callback(channel):
    global flow_rising_count
    flow_rising_count = flow_rising_count + 1


def gpio_init():
    try:
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

    except Exception as ex:
        logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in gpio_init: ' + repr(ex))
        send_email('General failure', 'Error in gpio_init: ' + repr(ex))


def schedule_morning_run():
    try:
        # Morning run takes into account today and yesterday
        minutes_morning = minutes('morning')

        send_email('Watering morning running: ',
                   'START_TIME_MORNING: ' + datetime.now().strftime('%H:%M:%S') + ' \n' +
                   'MINUTES_MORNING: ' + str(minutes_morning))
        logging.info(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Watering morning running: ' +
                     'START_TIME_MORNING: ' + datetime.now().strftime('%H:%M:%S') + ' \n' +
                     'MINUTES_MORNING: ' + str(minutes_morning))

        run_time = datetime.now()
        if minutes_morning != [0, 0, 0]:
            for i in range(0, len(CIRCUITS)):
                run_time = run_time + timedelta(seconds=DELAY_BETWEEN_CIRCUITS)
                background_scheduler.add_job(enable_valve, 'date', run_date=run_time, args=[CIRCUITS[i]])

                run_time = run_time + timedelta(minutes=minutes_morning[i], seconds=DELAY_BETWEEN_CIRCUITS)
                background_scheduler.add_job(disable_valve, 'date', run_date=run_time, args=[CIRCUITS[i]])

    except Exception as ex:
        logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in schedule_morning_run: ' + repr(ex))
        send_email('General failure', 'Error in schedule_morning_run: ' + repr(ex))


def schedule_night_run():
    try:
        # Night run takes into account just today
        minutes_night = minutes('night')

        send_email('Watering night running: ',
                   'START_TIME_NIGHT: ' + datetime.now().strftime('%H:%M:%S') + ' \n' +
                   'MINUTES_NIGHT: ' + str(minutes_night))
        logging.info(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Watering night running: ' +
                     'START_TIME_NIGHT: ' + datetime.now().strftime('%H:%M:%S') + ' \n' +
                     'MINUTES_NIGHT: ' + str(minutes_night))

        run_time = datetime.now()
        if minutes_night != [0, 0, 0]:
            for i in range(0, len(CIRCUITS)):
                run_time = run_time + timedelta(seconds=DELAY_BETWEEN_CIRCUITS)
                background_scheduler.add_job(enable_valve, 'date', run_date=run_time, args=[CIRCUITS[i]])

                run_time = run_time + timedelta(minutes=minutes_night[i], seconds=DELAY_BETWEEN_CIRCUITS)
                background_scheduler.add_job(disable_valve, 'date', run_date=run_time, args=[CIRCUITS[i]])

    except Exception as ex:
        logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in schedule_night_run: ' + repr(ex))
        send_email('General failure', 'Error in schedule_night_run: ' + repr(ex))


if __name__ == '__main__':
    try:
        logging.basicConfig(filename='simple_watering.log', level=logging.INFO)
        logging.info('------------------------------------------------------------')
        logging.info('------------------------System boot on: ' + datetime.now().strftime('%d/%m/%Y, %H:%M:%S'))
        logging.info('------------------------------------------------------------')

        background_scheduler = BackgroundScheduler()
        background_scheduler.start()

        # Create a log file for all apscheduler events
        aplogger = logging.getLogger('apscheduler')
        aplogger.propagate = False
        aplogger.setLevel(logging.INFO)
        aphandler = logging.FileHandler('apscheduler.log')
        aplogger.addHandler(aphandler)

        gpio_init()

        morning_run = datetime.now().replace(hour=START_TIME_MORNING.hour, minute=START_TIME_MORNING.minute,
                                             second=START_TIME_MORNING.second)
        night_run = datetime.now().replace(hour=START_TIME_NIGHT.hour, minute=START_TIME_NIGHT.minute,
                                           second=START_TIME_NIGHT.second)

        background_scheduler.add_job(schedule_morning_run, 'cron', hour=morning_run.hour, minute=morning_run.minute,
                                     second=morning_run.second)
        background_scheduler.add_job(schedule_night_run, 'cron', hour=night_run.hour, minute=night_run.minute,
                                     second=night_run.second)

        send_email('Watering calculation scheduled (program restart)',
                   'START_TIME_MORNING: ' + str(START_TIME_MORNING) + '\n' +
                   'START_TIME_NIGHT: ' + str(START_TIME_NIGHT))

        while True:
            t.sleep(1000)

    except Exception as ex:
        logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in __main__: ' + repr(ex))
        send_email('General failure', 'Error in __main__: ' + repr(ex))
