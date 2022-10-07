# Copyright 2020 Red Hat, Inc. All rights reserved.
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
from oslo_log import log as logging
from sqlalchemy import text

from octavia.i18n import _

LOG = logging.getLogger(__name__)


def check_database_connection(session):
    """This is a simple database connection check function.

    It will do a simple no-op query (low overhead) against the sqlalchemy
    session passed in.

    :param session: A Sql Alchemy database session.
    :returns: True if the connection check is successful, False if not.
    """
    try:
        session.execute(text('SELECT 1;'))
        return True, None
    except Exception as e:
        message = _('Database health check failed due to: {err}.').format(
            err=str(e))
        LOG.error(message)
        return False, message
