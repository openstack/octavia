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
from oslo_utils import timeutils
from sqlalchemy.orm import exc as sqlalchemy_exceptions

from octavia.common import constants
from octavia.controller.worker.v1 import controller_worker as cw1
from octavia.controller.worker.v2 import controller_worker as cw2
from octavia.db import api as db_api
from octavia.db import repositories as repo

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class SpareAmphora(object):
    def __init__(self):
        self.amp_repo = repo.AmphoraRepository()
        self.spares_repo = repo.SparesPoolRepository()
        self.az_repo = repo.AvailabilityZoneRepository()
        if CONF.api_settings.default_provider_driver == constants.AMPHORAV2:
            self.cw = cw2.ControllerWorker()
            self.check_booting_amphora = True
        else:
            self.cw = cw1.ControllerWorker()
            self.check_booting_amphora = False

    def spare_check(self):
        """Checks the DB for the Spare amphora count.

        If it's less than the requirement, starts new amphora.
        """
        lock_session = db_api.get_session(autocommit=False)
        session = db_api.get_session()
        try:
            # Lock the spares_pool record for read and write
            spare_amp_row = self.spares_repo.get_for_update(lock_session)

            conf_spare_cnt = CONF.house_keeping.spare_amphora_pool_size
            LOG.debug("Required Spare Amphora count : %d", conf_spare_cnt)
            availability_zones, links = self.az_repo.get_all(session,
                                                             enabled=True)
            compute_zones = set()
            for az in availability_zones:
                az_meta = self.az_repo.get_availability_zone_metadata_dict(
                    session, az.name)
                compute_zones.add(az_meta.get(constants.COMPUTE_ZONE))
            # If no AZs objects then build in the configured AZ (even if None)
            # Also if configured AZ is not None then also build in there
            # as could be different to the current AZs objects.
            if CONF.nova.availability_zone or not compute_zones:
                compute_zones.add(CONF.nova.availability_zone)

            amp_booting = []
            for az_name in compute_zones:
                # TODO(rm_work): If az_name is None, this will get ALL spares
                # across all AZs. This is the safest/most backwards compatible
                # way I can think of, as cached_zone on the amphora records
                # won't ever match. This should not impact any existing deploys
                # with no AZ configured, as the behavior should be identical
                # in that case. In the case of multiple AZs configured, it will
                # simply ensure there are at least <N> spares *somewhere*, but
                # will function more accurately if the operator actually
                # configures the AZ setting properly.
                curr_spare_cnt = self.amp_repo.get_spare_amphora_count(
                    session, availability_zone=az_name,
                    check_booting_amphora=self.check_booting_amphora)
                LOG.debug("Current Spare Amphora count for AZ %s: %d",
                          az_name, curr_spare_cnt)
                diff_count = conf_spare_cnt - curr_spare_cnt
                # When the current spare amphora is less than required
                if diff_count > 0:
                    LOG.info("Initiating creation of %d spare amphora "
                             "for az %s.", diff_count, az_name)

                    # Call Amphora Create Flow diff_count times
                    with futures.ThreadPoolExecutor(
                            max_workers=conf_spare_cnt) as executor:
                        for i in range(1, diff_count + 1):
                            LOG.debug("Starting amphorae number %d ...", i)
                            amp_booting.append(executor.submit(
                                self.cw.create_amphora, az_name))
                else:
                    LOG.debug("Current spare amphora count for AZ %s "
                              "satisfies the requirement", az_name)

            # Wait for the amphora boot threads to finish
            futures.wait(amp_booting)
            spare_amp_row.updated_at = timeutils.utcnow()
            lock_session.commit()
        except Exception:
            lock_session.rollback()


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
        if CONF.api_settings.default_provider_driver == constants.AMPHORAV2:
            self.cw = cw2.ControllerWorker()
        else:
            self.cw = cw1.ControllerWorker()

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
