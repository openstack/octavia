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

import collections
import json

import singleton


@singleton.singleton
class JSONFileConfig(collections.Mapping):
    def __init__(self):
        self.filename = None
        self.conf = {}
        self.observers = set()

    """ Set the config filename and perform the first read

    :param filename: a JSON file that contains the config
    """
    def set_filename(self, filename):
        self.filename = filename
        self.read_config()

    def __iter__(self):
        return iter(self.conf)

    def __getitem__(self, k):
        return self.conf[k]

    def __len__(self):
        return len(self.conf)

    """ Add a callable to be notified of config changes

    :param obs: a callable to receive change events
    """
    def add_observer(self, obs):
        self.observers.add(obs)

    """ Remove a callable to be notified of config changes

    By design if the callable passed doesn't exist then just return

    :param obs: a callable to attempt to remove
    """
    def remove_observer(self, obs):
        self.observers.discard(obs)

    """ Force a reread of the config file and inform all observers
    """
    def check_update(self):
        self.read_config()
        self.confirm_update()

    def confirm_update(self):
        for observer in self.observers:
            observer()

    def read_config(self):
        if self.filename is None:
            return

        self.cfile = open(self.filename, 'r')
        self.conf = json.load(self.cfile)
