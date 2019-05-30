import json
import requests
import urllib3
import statistics
from datetime import date
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
              + '/' + str(api_date.month).zfill(2) + '/'+str(api_date.day).zfill(2) + '?codiEstacio=CC'
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

            print(data)

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


if __name__ == '__main__':
    print(meteocat_api_request(date.today(), 'rh'))