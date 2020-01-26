import smbus2
import bme280

import argparse
import base64
import datetime
import json
import time

import jwt
import requests

#Cloud Iot CoreのAPI URL
_BASE_URL = 'https://cloudiotdevice.googleapis.com/v1'

#i2cのバスナンバー
_BUS_NUMBER = 1
#i2cのアドレス
_I2C_ADDRESS = 0x76

#バス
_BUS = smbus2.SMBus(_BUS_NUMBER)

#取得用の初期化パラメータ
_CALIBRATION_PARAMS = bme280.load_calibration_params(_BUS, _I2C_ADDRESS)


def readData():
    data = bme280.sample(_BUS, _I2C_ADDRESS, _CALIBRATION_PARAMS)

    datas = {'temperature':data.temperature ,
            'pressure':data.pressure, 'humidity':data.humidity}

    return datas


def create_message(id, longitude, latitude):
    datas = readData()

    #送信するメッセージをJSON形式にする
    message = '{{\
        "ID":{},\
        "LOCATION_LONGI":{},\
        "LOCATION_LATI":{},\
        "DEVICE_DATETIME":"{}",\
        "TEMPERATURE":{},\
        "PRESSURE":{},\
        "HUMIDITY":{}}}'.format(
                   id, longitude, latitude, datetime.datetime.now().
                   strftime('%Y-%m-%dT%H:%M:%S'),datas['temperature'],
                   datas['pressure'] ,datas['humidity'])
    return message


def create_jwt(project_id, private_key_file, algorithm):
    token = {
        # The time the token was issued.
        'iat': datetime.datetime.utcnow(),
        # Token expiration time.
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
        # The audience field should always be set to the GCP project id.
        'aud': project_id
    }

    # Read the private key file.
    with open(private_key_file, 'r') as f:
        private_key = f.read()

    #print('Creating JWT using {} from private key file {}'.format(
    #    algorithm, private_key_file))

    return jwt.encode(token, private_key, algorithm=algorithm).decode('ascii')


def publish_message(message, base_url, project_id, cloud_region, registry_id,
                    device_id, jwt_token):
    headers = {
        'authorization': 'Bearer {}'.format(jwt_token),
        'content-type': 'application/json',
        'cache-control': 'no-cache'
    }

    publish_url = (
        '{}/projects/{}/locations/{}/registries/{}/devices/{}:{}').format(
            base_url, project_id, cloud_region, registry_id, device_id,
            'publishEvent')

    #print('Publishing URL : \'{}\''.format(publish_url))

    body = None
    msg_bytes = base64.urlsafe_b64encode(message.encode('utf-8'))
    body = {'binary_data': msg_bytes.decode('ascii')}

    resp = requests.post(publish_url, data=json.dumps(body), headers=headers)

    return resp


def parse_command_line_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=(
        'Datasender to  Google Cloud IoT Core HTTP device connection code.'))
    parser.add_argument('--project_id',
                        required=True,
                        help='GCP cloud project name')
    parser.add_argument('--registry_id',
                        required=True,
                        help='Cloud IoT Core registry id')
    parser.add_argument('--device_id',
                        required=True,
                        help='Cloud IoT Core device id')
    parser.add_argument('--private_key_file',
                        required=True,
                        help='Path to private key file.')
    parser.add_argument(
        '--algorithm',
        choices=('RS256', 'ES256'),
        required=True,
        help='The encryption algorithm to use to generate the JWT.')
    parser.add_argument('--cloud_region',
                        default='asia-east1',
                        help='GCP cloud region')
    parser.add_argument(
        '--base_url',
        default=_BASE_URL,
        help=('Base URL for the Cloud IoT Core Device Service API'))
    parser.add_argument(
        '--id',
        default=999,
        type=int,
        help=('Device id, not IoT Core device id for unique key.'))
    parser.add_argument('--location_longitude',
                        default=0.0,
                        type=float,
                        help=('Longitude of this deice. ex)35.658581'))
    parser.add_argument('--location_latitude',
                        default=0.0,
                        type=float,
                        help=('Latitude of this deice. ex)139.745433'))

    return parser.parse_args()

def write_ng_data(message_data):
    datas = json.loads(message_data)
    #送信に失敗した場合、send_ng_message.txtファイルに送れなかったメッセージを書き込む。
    ng_message_file = open('send_ng_message.txt', 'a')
    ng_message_file.write(str(datas['ID']))
    ng_message_file.write(',')
    ng_message_file.write(str(datas['LOCATION_LONGI']))
    ng_message_file.write(',')
    ng_message_file.write(str(datas['LOCATION_LATI']))
    ng_message_file.write(',')
    ng_message_file.write(str(datas['DEVICE_DATETIME']))
    ng_message_file.write(',')
    ng_message_file.write(str(datas['TEMPERATURE']))
    ng_message_file.write(',')
    ng_message_file.write(str(datas['PRESSURE']))
    ng_message_file.write(',')
    ng_message_file.write(str(datas['HUMIDITY']))

    ng_message_file.write('\n')
    ng_message_file.close()


def send_message(args, jwt_token, jwt_iat, jwt_exp_mins):
    seconds_since_issue = (datetime.datetime.utcnow() - jwt_iat).seconds
    if seconds_since_issue > 60 * jwt_exp_mins:
        #print('Refreshing token after {}s').format(seconds_since_issue)
        jwt_token = create_jwt(args.project_id, args.private_key_file,
                               args.algorithm)
        jwt_iat = datetime.datetime.utcnow()

    message_data = create_message(args.id, args.location_longitude,
                                  args.location_latitude)

    #print('Publishing message : \'{}\''.format(message_data))

    try:
        resp = publish_message(message_data, args.base_url, args.project_id,
                               args.cloud_region, args.registry_id,
                               args.device_id, jwt_token)
    except:
        resp = None

    #On HTTP error , write datas to csv file.
    if (resp is None) or (resp.status_code != requests.codes.ok):
        write_ng_data(message_data)


def main():
    args = parse_command_line_args()

    jwt_token = create_jwt(args.project_id, args.private_key_file,
                           args.algorithm)
    jwt_iat = datetime.datetime.utcnow()

    # Publish mesages to the HTTP bridge once per 5 minites.
    while True:

        send_message(args, jwt_token, jwt_iat, 20)

        #5分に一度データを送信する
        time.sleep(300)


if __name__ == '__main__':
    main()
