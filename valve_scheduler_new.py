from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time, timedelta
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import minutes
import RPi.GPIO as GPIO

from minutes import minutes

GPIO_2_FLOW_METER = 13
GPIO_4_RIGHT = 16
GPIO_5_FAR = 18
GPIO_6_LEFT = 22

CIRCUITS = [GPIO_4_RIGHT, GPIO_5_FAR, GPIO_6_LEFT]
CIRCUIT_NAMES = dict([(GPIO_4_RIGHT, 'Right circuit'), (GPIO_5_FAR, 'Far circuit'), (GPIO_6_LEFT, 'Left circuit')])
DELAY_BETWEEN_CIRCUITS = 5

START_TIME_MORNING = time(17, 40, 0)
START_TIME_NIGHT = time(17, 50, 0)

MINUTES_MORNING = [20, 5, 20]
MINUTES_NIGHT = [8, 2, 8]

flow_rising_count = 0
real_start_time_s = None


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
    #GPIO.output(valve_id, GPIO.LOW)
    GPIO.add_event_detect(GPIO_2_FLOW_METER, GPIO.RISING, callback=sensor_callback)


def disable_valve(valve_id):
    GPIO.output(valve_id, GPIO.HIGH)
    GPIO.remove_event_detect(GPIO_2_FLOW_METER)

    global real_start_time_s
    real_stop_time_s = datetime.now()
    delta = real_stop_time_s - real_start_time_s
    print('delta', delta)
    pouring_time_s = delta.seconds
    print('pouring_time_s', pouring_time_s)

    global flow_rising_count
    flow_l_per_minute = (flow_rising_count / pouring_time_s) / 4.8
    print('flow_rising_count', flow_rising_count)
    print('flow_l_per_minute', flow_l_per_minute)
    volume = flow_l_per_minute * (pouring_time_s / 60)
    print('volume', volume)

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
    run_time = datetime.fromisoformat(run_time)

    send_email("Watering morning run scheduled: ",
               'START_TIME_MORNING: ' + datetime.now().strftime("%H:%M:%S") + '\n' +
               'MINUTES_MORNING: ' + str(minutes_morning))

    for i in range(0, len(CIRCUITS)):
        run_time = run_time + timedelta(seconds=DELAY_BETWEEN_CIRCUITS)
        background_scheduler.add_job(enable_valve, 'date', run_date=run_time, max_instances=1, args=[CIRCUITS[i]])

        run_time = run_time + timedelta(minutes=minutes_morning[i], seconds=DELAY_BETWEEN_CIRCUITS)
        background_scheduler.add_job(disable_valve, 'date', run_date=run_time, max_instances=1, args=[CIRCUITS[i]])


def schedule_night_run (run_time):
    # Night run takes into account just today
    [dummy, minutes_night] = minutes(0, 1)
    run_time = datetime.fromisoformat(run_time)

    send_email("Watering night run scheduled: ",
               'START_TIME_NIGHT: ' + datetime.now().strftime("%H:%M:%S") + '\n' +
               'MINUTES_NIGHT: ' + str(minutes_night))

    for i in range(0, len(CIRCUITS)):
        run_time = run_time + timedelta(seconds=DELAY_BETWEEN_CIRCUITS)
        background_scheduler.add_job(enable_valve, 'date', run_date=run_time, max_instances=1, args=[CIRCUITS[i]])

        run_time = run_time + timedelta(minutes=minutes_night[i], seconds=DELAY_BETWEEN_CIRCUITS)
        background_scheduler.add_job(disable_valve, 'date', run_date=run_time, max_instances=1, args=[CIRCUITS[i]])


if __name__ == '__main__':
    logging.basicConfig(filename='simple_watering.log', level=logging.INFO)
    logging.info('------------------------------------------------------------')
    logging.info('------------------------System boot on: ' + datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
    logging.info('------------------------------------------------------------')

    background_scheduler = BackgroundScheduler()
    background_scheduler.start()

    gpio_init()

    morning_run = datetime.now().replace(hour=START_TIME_MORNING.hour, minute=START_TIME_MORNING.minute,
                                         second=START_TIME_MORNING.second)
    night_run = datetime.now().replace(hour=START_TIME_NIGHT.hour, minute=START_TIME_NIGHT.minute,
                                       second=START_TIME_NIGHT.second)

    background_scheduler.add_job(schedule_morning_run, 'cron', args=morning_run.isoformat(), hour=morning_run.hour, minute=morning_run.minute,
                                 second=morning_run.second, id='schedule_morning_run', max_instances=1)
    background_scheduler.add_job(schedule_night_run, 'cron', args=str(night_run.isoformat), hour=night_run.hour, minute=night_run.minute,
                                 second=night_run.second, id='schedule_night_run', max_instances=1)

    send_email("Watering calculation scheduled (program restart)",
               'START_TIME_MORNING: ' + str(START_TIME_MORNING) + '\n' +
               'START_TIME_NIGHT: ' + str(START_TIME_NIGHT) + '\n' +
               'MINUTES_MORNING: ' + str(MINUTES_MORNING) + '\n' +
               'MINUTES_NIGHT: ' + str(MINUTES_NIGHT))

    while True:
        pass
