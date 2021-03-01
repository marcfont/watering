from apscheduler.schedulers.background import BackgroundScheduler
from datetime import date, time, timedelta, datetime
import time as t
import logging
import smtplib
import http.client
import requests
import ssl
import json
import statistics
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import RPi.GPIO as GPIO
import math
import urllib3
import subprocess
import configparser
# no need to worry about SSL to verify connection to meteo.cat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADER = {'x-api-key': 'yTLyU2J2XraoSZ4LEHpG35izWgS22AMs1DmRJqmZ'}

#GPIO_2_FLOW_METER = 13
#flow_rising_count = 0

# ------------------ READ CONFIG FILE ---------------------
config = configparser.ConfigParser()
config.read('valve_scheduler.conf')

START_TIME_MORNING = config['RUN']['RUNTIME']
MANUAL_MINUTES = config['RUN']['MANUAL_MINUTES_CALCULATION']
MINUTES = config['RUN']['MANUAL_MINUTES']

KJ = config['WATERING']['KJ'] 
EFFECTIVE_RAIN = config['WATERING']['EFFECTIVE_RAIN'] 
REAL_ETO_TO_MINUTES_SLOPE = config['WATERING']['REAL_ETO_TO_MINUTES_SLOPE'] 
STRAWBERRY_TO_GRASS = config['WATERING']['STRAWBERRY_TO_GRASS'] 
MIN_ETO_REAL = config['WATERING']['MIN_ETO_REAL'] 
DELAY_BETWEEN_CIRCUITS = config['WATERING']['CIRCUIT_DEFINITIONS'] 

CIRCUIT_DEFINITIONS = config['CIR']['CIRCUIT_DEFINITIONS'] 

real_start_time_s = None

def __evapo_yesterday_Oris():
	"""
		returns 24h accumulated evapotraspiration for the day before
	"""

	api_date = date.today()
	api_date = date.today() - timedelta(days=1)

	try:
		# url model --> https://api.meteo.cat/xema/v1/variables/cmv/6006/2021/02/23?codiEstacio=CC
		url = 'https://api.meteo.cat/xema/v1/variables/cmv/6006/' \
			  + str(api_date.year) + '/' + str(api_date.month).zfill(2) + '/' \
			  + str(api_date.day).zfill(2) + '?codiEstacio=CC'
		r = requests.get(url, headers=HEADER, verify=False)

		# sample:
		#	{"codi":6006,"lectures":
		# 		[
		#			{"data":"2021-02-23T00:00Z","valor":0,"estat":" ","baseHoraria":"HO"},
		# 			{"data":"2021-02-23T01:00Z","valor":0,"estat":" ","baseHoraria":"HO"}
		#		]
		#	}
		
		eto = 0.0
		if r.ok:
			data = json.loads(r.text)

			for d in data['lectures']:
				eto = eto + (d['valor'])
		else:
			# todo: error handling
			logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' ERROR #1 in __evapo_yesterday_Oris')
			
		# url model --> https://api.meteo.cat/xema/v1/variables/mesurades/36/2019/05/28?codiEstacio=CC
		url = 'https://api.meteo.cat/xema/v1/variables/mesurades/35/' \
			  + str(api_date.year) + '/' + str(api_date.month).zfill(2) + '/' \
			  + str(api_date.day).zfill(2) + '?codiEstacio=CC'
		r = requests.get(url, headers=HEADER, verify=False)
		
		rain = 0.0
		if r.ok:
			data = json.loads(r.text)

			for d in data['lectures']:
				rain = rain + (d['valor'])		
		
		return [eto, rain]

	except Exception as ex:
		logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in __evapo_yesterday_Oris: ' + repr(ex))
		send_email('General failure', 'Error in __evapo_yesterday_Oris: ' + repr(ex))


def minutes():
	try:
		[eto, rain] = __evapo_yesterday_Oris()
		eto_real = eto * KJ - rain * EFFECTIVE_RAIN

		if eto_real >= MIN_ETO_REAL:
			grass_minutes = eto_real * REAL_ETO_TO_MINUTES_SLOPE
			strawberry_minutes = grass_minutes * STRAWBERRY_TO_GRASS
			morning = [round(grass_minutes / 2), round(strawberry_minutes), round(grass_minutes / 2)]
			return morning
		else:
			return [0, 0, 0]

	except Exception as ex:
		logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in minutes: ' + repr(ex))
		send_email('General failure', 'Error in minutes: ' + repr(ex))


def print_minutes():
	print('Morning: ' + str(minutes()))
	
def send_email(subject, body):
	try:
		port = 465  # For SSL
		smtp_server = 'smtp.gmail.com'
		sender_email = 'watering.espona@gmail.com'
		receiver_email = 'marc.font@gmail.com'
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
		logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in send_email: ' + repr(ex))
		send_email('General failure', 'Error in send_email: ' + repr(ex))


def enable_valve(valve_id):
	try:
		logging.info(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Enable valve in pin: ' + str(valve_id))
		send_email('Enable', str(CIRCUIT_NAMES[valve_id]) + ' has been enabled.')

		global real_start_time_s
		real_start_time_s = datetime.now()
		GPIO.output(valve_id, GPIO.LOW)
		#GPIO.add_event_detect(GPIO_2_FLOW_METER, GPIO.RISING, callback=sensor_callback)

	except Exception as ex:
		logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in enable_valve: ' + repr(ex))
		send_email('General failure', 'Error in enable_valve: ' + repr(ex))


def disable_valve(valve_id):
	try:
		GPIO.output(valve_id, GPIO.HIGH)
		#GPIO.remove_event_detect(GPIO_2_FLOW_METER)

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


#def sensor_callback(channel):
#	global flow_rising_count
#	flow_rising_count = flow_rising_count + 1


def gpio_init():
	try:
		GPIO.setmode(GPIO.BOARD)
		GPIO.setwarnings(False)

		#GPIO.setup(GPIO_2_FLOW_METER, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

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


def schedule_daily_run():
	try:
		minutes_to_run = [0, 0, 0]
		if MANUAL_MINUTES:
			minutes_to_run = MINUTES
		else:
			minutes_to_run = minutes()

		send_email('Watering morning running: ',
				   'START_TIME_MORNING: ' + datetime.now().strftime('%H:%M:%S') + ' \n' +
				   'MINUTES_MORNING: ' + str(minutes_to_run))
		logging.info(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Watering morning running: \n' +
					 'START_TIME_MORNING: ' + datetime.now().strftime('%H:%M:%S') + ' \n' +
					 'MINUTES_MORNING: ' + str(minutes_to_run))
					 
		#TODO guardar a la DB (veure TODO.txt)

		run_time = datetime.now()
		if minutes_to_run != [0, 0, 0]:
			for i in range(0, len(CIRCUIT_DEFINITIONS)):
				run_time = run_time + timedelta(seconds=DELAY_BETWEEN_CIRCUITS)
				background_scheduler.add_job(enable_valve, 'date', run_date=run_time, args=[CIRCUIT_DEFINITIONS[i]['PORT'], CIRCUIT_DEFINITIONS[i]['NAME']])

				run_time = run_time + timedelta(minutes=minutes_to_run[i], seconds=DELAY_BETWEEN_CIRCUITS)
				background_scheduler.add_job(disable_valve, 'date', run_date=run_time, args=[CIRCUIT_DEFINITIONS[i]['PORT'], CIRCUIT_DEFINITIONS[i]['NAME']])

	except Exception as ex:
		logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in schedule_daily_run: ' + repr(ex))
		send_email('General failure', 'Error in schedule_daily_run: ' + repr(ex))


def wait_for_network():
	""" # wait until Internet connection comes up"""
	try:
		# Wait for eth0 to come up
		eth_down = True
		while eth_down:
			if subprocess.getoutput('hostname -I') == "":
				time.sleep(2)
			else:
				eth_down = False
				logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Awaiting WLAN to come up')

		# wait for Internet to be available
		internet_down = True
		while internet_down:
			if "0 received" in subprocess.getoutput('ping 8.8.8.8 -c 1'):
				time.sleep(2)
			else:
				internet_down = False
				logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Awaiting Internet to come up')

	except Exception as ex:
		logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in wait_for_network: ' + repr(ex))
		# this may fail anyway
		send_email('General failure', 'Error in wait_for_network: ' + repr(ex))


if __name__ == '__main__':
	try:
		logging.basicConfig(filename='watering.log', level=logging.INFO)
		logging.info('------------------------------------------------------------')
		logging.info('------------------------System boot on: ' + datetime.now().strftime('%d/%m/%Y, %H:%M:%S'))
		logging.info('------------------------MORNING_RUN_ENABLED: True')
		logging.info('------------------------START_TIME_MORNING: ' + str(START_TIME_MORNING))
		if MANUAL_MINUTES:
			logging.info('------------------------MANUAL_MINUTES: ' + str(MANUAL_MINUTES))
			logging.info('------------------------MINUTES: ' + str(MINUTES))		
		logging.info('------------------------------------------------------------')

		wait_for_network()

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

		background_scheduler.add_job(schedule_daily_run, 'cron', hour=morning_run.hour, minute=morning_run.minute,
									 second=morning_run.second)
		
		content = 'MORNING_RUN_ENABLED: True' + '\n' +\
		'START_TIME_MORNING: ' + str(START_TIME_MORNING)

		if MANUAL_MINUTES:
			content = content + '\nMANUAL_MINUTES: ' + str(MANUAL_MINUTES) + '\n' +\
			'MINUTES: ' + str(MINUTES)
				   
		send_email('Watering calculation scheduled (program restart)', content)

		while True:
			t.sleep(1000)

	except Exception as e:
		logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in __main__: ' + repr(e))
		send_email('General failure', 'Error in __main__: ' + repr(e))
