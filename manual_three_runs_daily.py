import sys
from valve_scheduler import *


START_TIME_1 = t.strptime("11:41:00", '%H:%M:%S')
START_TIME_2 = t.strptime("11:46:00", '%H:%M:%S')
START_TIME_3 = t.strptime("11:51:00", '%H:%M:%S')

DELAY_BETWEEN_CIRCUITS = 5

def self_kill():
	sys.exit()

if __name__ == '__main__':
	background_scheduler = BackgroundScheduler()
	background_scheduler.start()
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
