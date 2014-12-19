#! /usr/bin/env python

#    Copyright 2014 Hewlett-Packard Development Company, L.P.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import argparse
import sys
import time

import config
import health_sender


def run_sender():
    sender = health_sender.UDPStatusSender()
    cfg = config.JSONFileConfig()

    sighup_received = False
    seq = 0
    while True:
        if sighup_received:
            print('re-reading config file')
            sighup_received = False
            cfg.check_update()

        message = {'not the answer': 43,
                   'id': cfg['id'],
                   'seq': seq}
        seq = seq + 1
        sender.dosend(message)
        time.sleep(cfg['delay'])


def parse_args():
    parser = argparse.ArgumentParser(description='Health Sender Daemon')
    parser.add_argument('-c', '--config', type=str, required=False,
                        help='config file path',
                        default='/etc/amphora/status_sender.json')
    args = parser.parse_args()
    return vars(args)


if __name__ == '__main__':
    args = parse_args()
    cfg = config.JSONFileConfig()
    try:
        cfg.set_filename(args['config'])
    except IOError as exception:
        print(exception)
        sys.exit(1)

    # Now start up the sender loop
    run_sender()
    sys.exit(0)
