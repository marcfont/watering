import json
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def mc_get_max_temperatures():
    # https://3.python-requests.org/
    # todo: implement

    try:
        headers = {'x-api-key': 'yTLyU2J2XraoSZ4LEHpG35izWgS22AMs1DmRJqmZ'}
        url = 'https://api.meteo.cat/xema/v1/variables/mesurades/36/2019/05/27?codiEstacio=CC'
        r = requests.get(url, headers=headers, verify=False)


        # sample:
        # {'codi': 35, 'lectures':
        # [{'data': '2019-05-03T00:00Z', 'valor': 0.5, 'estat': 'V', 'baseHoraria': 'SH'},
        # {'data': '2019-05-03T00:30Z', 'valor': 0, 'estat': 'V', 'baseHoraria': 'SH'}]}
        data = json.loads(r.text)

        if r.ok:
            for d in data["lectures"]:
                print(d["valor"])


    except ConnectionError as ex:
        print('Exception thrown: ConnectionError')
        print(ex)
    except requests.exceptions.RequestException as ex:
        print('Exception thrown: requests.exceptions.RequestException')
        print(ex)


if __name__ == '__main__':
    mc_get_max_temperatures()