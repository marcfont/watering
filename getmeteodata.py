import json
import requests
import urllib3
import statistics
from datetime import date, timedelta
import math

# no need to worry about SSL to verify connection to meteo.cat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADER = {'x-api-key': 'yTLyU2J2XraoSZ4LEHpG35izWgS22AMs1DmRJqmZ'}


def meteocat_api_request(api_date, param):
    """
    day(date), day to get the data from
    param(String):
    temp-->32 returns [max, min]
    rain-->35 returns [sum()]
    rh-->33 returns [max, min]
    rad->36 returns [calculation()], see readme.md
    wind->30 returns [mean()]
    """
    operations = {'temp': '32', 'rain': '35', 'rh': '33', 'rad': '36', 'wind': '30'}

    if type(api_date) is not date:
        raise TypeError('First parameter must be datetime.dat, not %s' % type(api_date))
    if not operations.__contains__(param):
        raise TypeError('Second parameter has unaccepted value %s' % param)

    try:
        # url model --> https://api.meteo.cat/xema/v1/variables/mesurades/36/2019/05/28?codiEstacio=CC
        url = 'https://api.meteo.cat/xema/v1/variables/mesurades/' + str(operations[param]) + '/' + str(api_date.year) \
              + '/' + str(api_date.month).zfill(2) + '/' + str(api_date.day).zfill(2) + '?codiEstacio=CC'
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

            if param == 'temp' or param == 'rh':
                return [max(values), min(values)]
            elif param == 'rain':
                return sum(values)
            elif param == 'rad':
                # Irradiació = (average(irradiància) * segons en el període) / 1000000
                return statistics.mean(values) * 60 * 30 * len(values) / 1000000
            elif param == 'wind':
                return statistics.mean(values)
        else:
            # todo: error handling
            print(r)

    except ConnectionError as ex:
        print('Exception thrown: ConnectionError')
        print(ex)
    except requests.exceptions.RequestException as ex:
        print('Exception thrown: requests.exceptions.RequestException')
        print(ex)


def evapotranspiration_rain_day(when):
    [t_max, t_min] = meteocat_api_request(when, 'temp')
    rain = meteocat_api_request(when, 'rain')
    [rh_max, rh_min] = meteocat_api_request(when, 'rh')
    rn_g = meteocat_api_request(when, 'rad')
    u2 = meteocat_api_request(when, 'wind')

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

    return [round(et0, 1), round(rain, 1)]


if __name__ == '__main__':
    d = 2
    print(evapotranspiration_rain_day(date.today()-timedelta(days=d)))
