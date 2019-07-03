from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time, timedelta
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import RPi.GPIO as GPIO


GPIO_2_FLOW_METER = 13
GPIO_4_RIGHT = 16
GPIO_5_FAR = 18
GPIO_6_LEFT = 22

CIRCUITS = [GPIO_4_RIGHT, GPIO_5_FAR, GPIO_6_LEFT]
CIRCUIT_NAMES = dict([(GPIO_4_RIGHT, 'Right circuit'), (GPIO_5_FAR, 'Far circuit'), (GPIO_6_LEFT, 'Left circuit')])

START_TIME_MORNING = time(6, 0, 0)
START_TIME_NIGHT = time(22, 0, 0)

MINUTES_MORNING = [20, 6, 20]
MINUTES_NIGHT = [6, 2, 6]

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
    logging.info("Now watering........")
    send_email("Enable", str(CIRCUIT_NAMES[valve_id]) + " has been enabled.")

    global real_start_time_s
    real_start_time_s = time.time()
    GPIO.output(valve_id, GPIO.LOW)
    GPIO.add_event_detect(GPIO_2_FLOW_METER, GPIO.RISING, callback=sensor_callback)


def disable_valve(valve_id):
    GPIO.output(valve_id, GPIO.HIGH)
    GPIO.remove_event_detect(GPIO_2_FLOW_METER)

    global real_start_time_s
    real_stop_time_s = time.time()
    pouring_time_s = real_stop_time_s - real_start_time_s

    global flow_rising_count

    flow = (flow_rising_count / pouring_time_s) / 4.8

    send_email("Disable", str(CIRCUIT_NAMES[valve_id]) + " has been disabled.\nWatering volume has been "
               + str(round(flow)) + " liters.")

    logging.info("..............and watering stops")
    logging.info("Disable valve in pin: " + str(valve_id))
    logging.info("Watering volume has been " + str(round(flow)) + " liters")


def sensor_callback(channel):
    global flow_rising_count
    flow_rising_count = flow_rising_count + 1


def gpio_init():
    GPIO.setmode(GPIO.BOARD)

    GPIO.setup(GPIO_2_FLOW_METER, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.setup(GPIO_4_RIGHT, GPIO.OUT)
    GPIO.setup(GPIO_5_FAR, GPIO.OUT)
    GPIO.setup(GPIO_6_LEFT, GPIO.OUT)

    # this shouldn't be needed but here it comes just in case
    GPIO.output(GPIO_4_RIGHT, GPIO.HIGH)
    GPIO.output(GPIO_5_FAR, GPIO.HIGH)
    GPIO.output(GPIO_6_LEFT, GPIO.HIGH)


if __name__ == '__main__':
    logging.basicConfig(filename='simple_watering.log', level=logging.INFO)
    logging.info('---------------------------------------------')
    logging.info('---------------system boot-------------------')
    logging.info('---------------------------------------------')

    background_scheduler = BackgroundScheduler()
    background_scheduler.start()

    gpio_init()

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
        # morning_run = morning_run + timedelta(seconds=MINUTES_MORNING[i]+1)
        background_scheduler.add_job(disable_valve, 'cron', hour=morning_run.hour, minute=morning_run.minute,
                                     second=morning_run.second, max_instances=1, args=[CIRCUITS[i]])

        # run once a day at START_TIME_NIGHT + 1 second for MINUTES_NIGHT[i] minutes
        night_run = night_run + timedelta(seconds=1)
        background_scheduler.add_job(enable_valve, 'cron', hour=night_run.hour, minute=night_run.minute,
                                     second=night_run.second, max_instances=1, args=[CIRCUITS[i]])

        night_run = night_run + timedelta(minutes=MINUTES_NIGHT[i], seconds=1)
        # night_run = night_run + timedelta(seconds=MINUTES_NIGHT[i]+1)
        background_scheduler.add_job(disable_valve, 'cron', hour=night_run.hour, minute=night_run.minute,
                                     second=night_run.second, max_instances=1, args=[CIRCUITS[i]])

    logging.info(background_scheduler.print_jobs())
    send_email("Watering scheduled (program restart)", str(background_scheduler.print_jobs()))

    while True:
        pass
