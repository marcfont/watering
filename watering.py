from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import time


class WateringCycle:
    def __init__(self, circuit, start_date, duration, volume):
        self.circuit = circuit
        self.start_date = start_date
        self.duration = duration
        self.volume = volume


class Circuit:
    def __init__(self, name, valve_id):
        self.name = name
        self.valve_id = valve_id


def enable_valve(port):
    # do whatever
    port = 0


def disable_valve(port):
    # do whatever
    port = 0

# IMPORTANT: En cas de pluja i a partir d’una pluviometria
# de 10 mm, s’anul·larà el reg.


# https://ajuntament.barcelona.cat/ecologiaurbana/sites/default/files/Manual-Reg-Parcs-Jardins.pdf
def evapotranspiracio():
    # anything between 0.5 and 0.65 would be reasonable
    kj = 0.5
    # between 8 and 20 mm/h
    # TODO: this has to be calculated when cudalimeter is in place
    cabal_l_m2_h = 14
    # percentage
    cu = 80
    # 2.4 cal?
    dosi_cm = 25
    precipitacio_mitjana_l_h = 900*6


def compute_watering_times():
    # TODO Implement this
    return 0


#############################################
# main logic


if __name__ == '__main__':
    START_TIME = time(22, 00, 00)
    DELAY_BETWEEN_CIRCUITS = time(00, 00, 5)

    LEFT_CIRCUIT = 1
    RIGHT_CIRCUIT = 2
    FAR_CIRCUIT = 3

    compute_scheduled = False

    background_scheduler = BackgroundScheduler()
    blocking_scheduler = BlockingScheduler()
    blocking_scheduler.start()

    while True:
        if not compute_scheduled:
            scheduler.add_job(compute_watering_times,
                              'cron', max_instances=1, hour=START_TIME.hour, minute=START_TIME.minute)
            # scheduler.add_job(enable_valve(1), 'cron', hour=22, minute=00)
            # scheduler.add_job(disable_valve(1), 'cron', hour=22, minute=15)