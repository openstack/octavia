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

from concurrent import futures
import datetime

from oslo_config import cfg
from oslo_log import log as logging
from sqlalchemy.orm import exc as sqlalchemy_exceptions

from octavia.common import constants
from octavia.controller.worker.v1 import controller_worker as cw1
from octavia.controller.worker.v2 import controller_worker as cw2
from octavia.db import api as db_api
from octavia.db import repositories as repo

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class DatabaseCleanup(object):
    def __init__(self):
        self.amp_repo = repo.AmphoraRepository()
        self.amp_health_repo = repo.AmphoraHealthRepository()
        self.lb_repo = repo.LoadBalancerRepository()

    def delete_old_amphorae(self):
        """Checks the DB for old amphora and deletes them based on its age."""
        exp_age = datetime.timedelta(
            seconds=CONF.house_keeping.amphora_expiry_age)

        session = db_api.get_session()
        amp_ids = self.amp_repo.get_all_deleted_expiring(session,
                                                         exp_age=exp_age)

        for amp_id in amp_ids:
            # If we're here, we already think the amp is expiring according to
            # the amphora table. Now check it is expired in the health table.
            # In this way, we ensure that amps aren't deleted unless they are
            # both expired AND no longer receiving zombie heartbeats.
            if self.amp_health_repo.check_amphora_health_expired(
                    session, amp_id, exp_age):
                LOG.debug('Attempting to purge db record for Amphora ID: %s',
                          amp_id)
                self.amp_repo.delete(session, id=amp_id)
                try:
                    self.amp_health_repo.delete(session, amphora_id=amp_id)
                except sqlalchemy_exceptions.NoResultFound:
                    pass  # Best effort delete, this record might not exist
                LOG.info('Purged db record for Amphora ID: %s', amp_id)

    def cleanup_load_balancers(self):
        """Checks the DB for old load balancers and triggers their removal."""
        exp_age = datetime.timedelta(
            seconds=CONF.house_keeping.load_balancer_expiry_age)

        session = db_api.get_session()
        lb_ids = self.lb_repo.get_all_deleted_expiring(session,
                                                       exp_age=exp_age)

        for lb_id in lb_ids:
            LOG.info('Attempting to delete load balancer id : %s', lb_id)
            self.lb_repo.delete(session, id=lb_id)
            LOG.info('Deleted load balancer id : %s', lb_id)


class CertRotation(object):
    def __init__(self):
        self.threads = CONF.house_keeping.cert_rotate_threads
        if CONF.api_settings.default_provider_driver == constants.AMPHORAV1:
            self.cw = cw1.ControllerWorker()
        else:
            self.cw = cw2.ControllerWorker()

    def rotate(self):
        """Check the amphora db table for expiring auth certs."""
        amp_repo = repo.AmphoraRepository()

        with futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
            session = db_api.get_session()
            rotation_count = 0
            while True:
                amp = amp_repo.get_cert_expiring_amphora(session)
                if not amp:
                    break
                rotation_count += 1
                LOG.debug("Cert expired amphora's id is: %s", amp.id)
                executor.submit(self.cw.amphora_cert_rotation, amp.id)
            if rotation_count > 0:
                LOG.info("Rotated certificates for %s amphora", rotation_count)
