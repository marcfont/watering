import sys
from valve_scheduler import *


START_TIME_1 = t.strptime("06:00:00", '%H:%M:%S')
START_TIME_2 = t.strptime("14:00:00", '%H:%M:%S')
START_TIME_3 = t.strptime("22:00:00", '%H:%M:%S')

DELAY_BETWEEN_CIRCUITS = 5

def schedule_daily_run():
	try:
		minutes_to_run = [0, 0, 0]
		if MANUAL_MINUTES:
			minutes_to_run = []
			for i in range(len(CIRCUIT_DEFINITIONS)):
				minutes_to_run.append(int(CIRCUIT_DEFINITIONS[i]['MANUAL_MINUTES']))
		else:
			minutes_to_run = minutes()

		send_email('Watering cycle running: \n',
				   'START_TIME: ' + datetime.now().strftime('%H:%M:%S') + ' \n' +
				   'CYCLE_MINUTES: ' + str(minutes_to_run))
		logging.info(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Watering cycle running: \n' +
					 'START_TIME: ' + datetime.now().strftime('%H:%M:%S') + ' \n' +
					 'CYCLE_MINUTES: ' + str(minutes_to_run))
					 
		#TODO guardar a la DB (veure TODO.txt)

		run_time = datetime.now()
		if minutes_to_run != [0, 0, 0]:
			for i in range(0, len(CIRCUIT_DEFINITIONS)):
				run_time = run_time + timedelta(seconds=DELAY_BETWEEN_CIRCUITS)
				background_scheduler.add_job(enable_valve, 'date', run_date=run_time, 
							args=[int(CIRCUIT_DEFINITIONS[i]['PORT']), CIRCUIT_DEFINITIONS[i]['NAME']])

				run_time = run_time + timedelta(minutes=minutes_to_run[i], seconds=DELAY_BETWEEN_CIRCUITS)
				background_scheduler.add_job(disable_valve, 'date', run_date=run_time, 
							args=[int(CIRCUIT_DEFINITIONS[i]['PORT']), CIRCUIT_DEFINITIONS[i]['NAME']])

	except Exception as ex:
		logging.error(datetime.now().strftime('%d/%m/%Y, %H:%M:%S') + ' Error in schedule_daily_run: ' + traceback.print_exc())
		send_email('General failure', 'Error in schedule_daily_run: ' + traceback.print_exc())

if __name__ == '__main__':
	logging.basicConfig(filename='watering.log', level=logging.INFO)
	
	background_scheduler = BackgroundScheduler()
	background_scheduler.start()

    # Create a log file for all apscheduler events
	aplogger = logging.getLogger('apscheduler')
	aplogger.propagate = False
	aplogger.setLevel(logging.INFO)
	aphandler = logging.FileHandler('apscheduler.log')
	aplogger.addHandler(aphandler)

	gpio_init()

	background_scheduler.add_job(schedule_daily_run, 'cron', hour = int(t.strftime('%H', START_TIME_1)),
                                                             minute = int(t.strftime('%M', START_TIME_1)),
                                                             second = int(t.strftime('%S', START_TIME_1)))

	background_scheduler.add_job(schedule_daily_run, 'cron', hour = int(t.strftime('%H', START_TIME_2)),
                                                             minute = int(t.strftime('%M', START_TIME_2)),
                                                             second = int(t.strftime('%S', START_TIME_2)))

	background_scheduler.add_job(schedule_daily_run, 'cron', hour = int(t.strftime('%H', START_TIME_3)),
                                                             minute = int(t.strftime('%M', START_TIME_3)),
                                                             second = int(t.strftime('%S', START_TIME_3)))

	while True:
		pass
