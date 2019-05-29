import json
import requests
import urllib3
from datetime import datetime, timedelta
# no need to worry about SSL to verify connection to meteo.cat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADER = {'x-api-key': 'yTLyU2J2XraoSZ4LEHpG35izWgS22AMs1DmRJqmZ'}

def mc_get_temperatures_24h():
    try:
        now = datetime.utcnow()
        # url model --> https://api.meteo.cat/xema/v1/variables/mesurades/36/2019/05/28?codiEstacio=CC
        url = 'https://api.meteo.cat/xema/v1/variables/mesurades/36/' + str(now.year) + '/' + str(now.month).zfill(2) \
              + '/'+str(now.day).zfill(2) + '?codiEstacio=CC'
        r = requests.get(url, headers=HEADER, verify=False)

        # sample:
        # {'codi': 35, 'lectures':
        # [{'data': '2019-05-03T00:00Z', 'valor': 0.5, 'estat': 'V', 'baseHoraria': 'SH'},
        # {'data': '2019-05-03T00:30Z', 'valor': 0, 'estat': 'V', 'baseHoraria': 'SH'}]}
        data = json.loads(r.text)

        now = now - timedelta(days=1)
        url2 = 'https://api.meteo.cat/xema/v1/variables/mesurades/36/' + str(now.year) + '/' + str(now.month).zfill(2) \
              + '/'+str(now.day).zfill(2) + '?codiEstacio=CC'
        r2 = requests.get(url2, headers=HEADER, verify=False)
        data2 = json.loads(r2.text)

        # dt = datetime.strptime('2019-05-03T00:00Z', '%Y-%m-%dT%H:%MZ')

        if r.ok:
            for d in data["lectures"]:
                print(d["valor"])
        else:
            print('error')

    except ConnectionError as ex:
        print('Exception thrown: ConnectionError')
        print(ex)
    except requests.exceptions.RequestException as ex:
        print('Exception thrown: requests.exceptions.RequestException')
        print(ex)


if __name__ == '__main__':
    mc_get_temperatures()