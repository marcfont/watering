from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time, timedelta

MINUTES = [0.1, 0.1, 0.1]
DELAY_BETWEEN_CIRCUITS = 5

def enable_valve():
	print('running enable_valve')


def disable_valve():
	print('running disable_valve')


if __name__ == '__main__':
	background_scheduler = BackgroundScheduler()
	background_scheduler.start()

	run_time = datetime.now()
	
	for i in range(0, len(MINUTES)):
		run_time = run_time + timedelta(seconds=DELAY_BETWEEN_CIRCUITS)
		background_scheduler.add_job(enable_valve, 'date', run_date=run_time)

		run_time = run_time + timedelta(seconds=DELAY_BETWEEN_CIRCUITS + MINUTES[i] * 60)
		background_scheduler.add_job(disable_valve, 'date', run_date=run_time)	
	
    
	while True:
		pass