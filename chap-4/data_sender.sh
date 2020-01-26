#!/bin/bash

python3 data_sender.py --project_id hyakuyo-bako \
                       --registry_id device_registry \
                       --device_id ID001\
                       --private_key_file ./rsa_private.pem\
                       --algorithm RS256\
                       --cloud_region asia-east1\
                       --id 1
