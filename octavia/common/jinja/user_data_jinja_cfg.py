# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import os

import jinja2

from octavia.common.config import cfg
from octavia.common import constants

CONF = cfg.CONF

TEMPLATES_DIR = (os.path.dirname(os.path.realpath(__file__)) +
                 constants.TEMPLATES + '/')


class UserDataJinjaCfg(object):

    def __init__(self):
        template_loader = jinja2.FileSystemLoader(searchpath=os.path.dirname(
            TEMPLATES_DIR))
        jinja_env = jinja2.Environment(autoescape=True, loader=template_loader)
        self.agent_template = jinja_env.get_template(
            constants.USER_DATA_CONFIG_DRIVE_TEMPLATE)

    def build_user_data_config(self, user_data):
        return self.agent_template.render(user_data=user_data)
