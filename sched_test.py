from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time, timedelta

START_TIME_MORNING = time(13, 22, 0)
START_TIME_NIGHT = time(13, 24, 0)

START_TIME_MORNING_2 = time(13, 26, 0)
START_TIME_NIGHT_2 = time(13, 28, 0)

DELAY_BETWEEN_CIRCUITS = 3


def enable_valve():
    print('running enable_valve')


def disable_valve():
    print('running disable_valve')


def schedule_morning_run():
    print('running schedule_morning_run')

    seconds_first = [5, 5, 5]

    run_time = datetime.now()

    for i in range(0, 3):
        run_time = run_time + timedelta(seconds=DELAY_BETWEEN_CIRCUITS)
        background_scheduler.add_job(enable_valve, 'date', run_date=run_time)

        run_time = run_time + timedelta(seconds=DELAY_BETWEEN_CIRCUITS + seconds_first[i])
        background_scheduler.add_job(disable_valve, 'date', run_date=run_time)


def schedule_night_run():
    print('running schedule_night_run')

    seconds_second = [7, 7, 7]

    run_time = datetime.now()

    for i in range(0, 3):
        run_time = run_time + timedelta(seconds=DELAY_BETWEEN_CIRCUITS)
        background_scheduler.add_job(enable_valve, 'date', run_date=run_time)

        run_time = run_time + timedelta(seconds=DELAY_BETWEEN_CIRCUITS + seconds_second)
        background_scheduler.add_job(disable_valve, 'date', run_date=run_time)


if __name__ == '__main__':
    background_scheduler = BackgroundScheduler()
    background_scheduler.start()

    morning_run = datetime.now().replace(hour=START_TIME_MORNING.hour, minute=START_TIME_MORNING.minute,
                                         second=START_TIME_MORNING.second)
    night_run = datetime.now().replace(hour=START_TIME_NIGHT.hour, minute=START_TIME_NIGHT.minute,
                                       second=START_TIME_NIGHT.second)

    morning_run_2 = datetime.now().replace(hour=START_TIME_MORNING_2.hour, minute=START_TIME_MORNING_2.minute,
                                           second=START_TIME_MORNING_2.second)
    night_run_2 = datetime.now().replace(hour=START_TIME_NIGHT.hour, minute=START_TIME_NIGHT.minute,
                                         second=START_TIME_NIGHT.second)

    background_scheduler.add_job(schedule_morning_run, 'cron', hour=morning_run.hour, minute=morning_run.minute,
                                 second=morning_run.second, max_instances=1)
    background_scheduler.add_job(schedule_night_run, 'cron', hour=night_run.hour, minute=night_run.minute,
                                 second=night_run.second, max_instances=1)
    background_scheduler.add_job(schedule_morning_run, 'cron', hour=morning_run_2.hour, minute=morning_run_2.minute,
                                 second=morning_run_2.second, max_instances=1)
    background_scheduler.add_job(schedule_night_run, 'cron', hour=night_run_2.hour, minute=night_run_2.minute,
                                 second=night_run_2.second, max_instances=1)

    while True:
        pass
