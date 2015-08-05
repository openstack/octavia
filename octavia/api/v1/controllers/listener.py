#    Copyright 2014 Rackspace
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

import logging

from oslo_db import exception as odb_exceptions
from oslo_utils import excutils
import pecan
from wsme import types as wtypes
from wsmeext import pecan as wsme_pecan

from octavia.api.v1.controllers import base
from octavia.api.v1.controllers import pool
from octavia.api.v1.types import listener as listener_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.db import api as db_api
from octavia.i18n import _LI


LOG = logging.getLogger(__name__)


class ListenersController(base.BaseController):

    def __init__(self, load_balancer_id):
        super(ListenersController, self).__init__()
        self.load_balancer_id = load_balancer_id
        self.handler = self.handler.listener

    @staticmethod
    def _secure_data(listener):
        # TODO(blogan): Handle this data when certificate management code is
        # available
        listener.tls_termination = wtypes.Unset

    @wsme_pecan.wsexpose(listener_types.ListenerResponse, wtypes.text)
    def get_one(self, id):
        """Gets a single listener's details."""
        session = db_api.get_session()
        db_listener = self.repositories.listener.get(
            session, load_balancer_id=self.load_balancer_id, id=id)
        if not db_listener:
            LOG.info(_LI("Listener %s not found.") % id)
            raise exceptions.NotFound(
                resource=data_models.Listener._name(), id=id)
        return self._convert_db_to_type(db_listener,
                                        listener_types.ListenerResponse)

    @wsme_pecan.wsexpose([listener_types.ListenerResponse])
    def get_all(self):
        """Lists all listeners on a load balancer."""
        session = db_api.get_session()
        db_listeners = self.repositories.listener.get_all(
            session, load_balancer_id=self.load_balancer_id)
        return self._convert_db_to_type(db_listeners,
                                        [listener_types.ListenerResponse])

    def _test_lb_status_post(self, session, lb_repo):
        """Verify load balancer is in a mutable status for post method."""
        if not lb_repo.test_and_set_provisioning_status(
                session, self.load_balancer_id, constants.PENDING_UPDATE):
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            LOG.info(_LI("Load Balancer %s is immutable.") % db_lb.id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)

    def _validate_listeners(self, session, lb_repo, listener_dict):
        """Validate listeners for wrong protocol or duplicate listeners

        Update the load balancer db when provisioning status changes.
        """
        try:
            sni_container_ids = listener_dict.pop('sni_containers')
            db_listener = self.repositories.listener.create(
                session, **listener_dict)
            if sni_container_ids is not None:
                for container_id in sni_container_ids:
                    sni_dict = {'listener_id': db_listener.id,
                                'tls_container_id': container_id}
                    self.repositories.sni.create(session, **sni_dict)
                db_listener = self.repositories.listener.get(session,
                                                             id=db_listener.id)
        except odb_exceptions.DBDuplicateEntry as de:
            # Setting LB back to active because this is just a validation
            # failure
            lb_repo.update(session, self.load_balancer_id,
                           provisioning_status=constants.ACTIVE)
            if ['id'] == de.columns:
                raise exceptions.IDAlreadyExists()
            elif set(['load_balancer_id', 'protocol_port']) == set(de.columns):
                raise exceptions.DuplicateListenerEntry(
                    port=listener_dict.get('protocol_port'))
        except odb_exceptions.DBError:
            # Setting LB back to active because this is just a validation
            # failure
            lb_repo.update(session, self.load_balancer_id,
                           provisioning_status=constants.ACTIVE)
            raise exceptions.InvalidOption(value=listener_dict.get('protocol'),
                                           option='protocol')
        try:
            LOG.info(_LI("Sending Creation of Listener %s to handler") %
                     db_listener.id)
            self.handler.create(db_listener)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    session, db_listener.id,
                    provisioning_status=constants.ERROR)
        db_listener = self.repositories.listener.get(
            session, id=db_listener.id)
        return self._convert_db_to_type(db_listener,
                                        listener_types.ListenerResponse)

    @wsme_pecan.wsexpose(listener_types.ListenerResponse,
                         body=listener_types.ListenerPOST, status_code=202)
    def post(self, listener):
        """Creates a listener on a load balancer."""
        self._secure_data(listener)
        session = db_api.get_session()
        lb_repo = self.repositories.load_balancer
        self._test_lb_status_post(session, lb_repo)
        listener_dict = listener.to_dict()
        listener_dict['load_balancer_id'] = self.load_balancer_id
        listener_dict['provisioning_status'] = constants.PENDING_CREATE
        listener_dict['operating_status'] = constants.OFFLINE
        # NOTE(blogan): Throwing away because we should not store secure data
        # in the database nor should we send it to a handler.
        if 'tls_termination' in listener_dict:
            del listener_dict['tls_termination']
        # This is the extra validation layer for wrong protocol or duplicate
        # listeners on the same load balancer.
        return self._validate_listeners(session, lb_repo, listener_dict)

    def _test_lb_status_put(self, session, id):
        """Test load balancer status for put method."""
        if not self.repositories.test_and_set_lb_and_listener_prov_status(
                session, self.load_balancer_id, id, constants.PENDING_UPDATE,
                constants.PENDING_UPDATE):
            LOG.info(_LI("Load Balancer %s is immutable.") %
                     self.load_balancer_id)
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)

    @wsme_pecan.wsexpose(listener_types.ListenerResponse, wtypes.text,
                         body=listener_types.ListenerPUT, status_code=202)
    def put(self, id, listener):
        """Updates a listener on a load balancer."""
        self._secure_data(listener)
        session = db_api.get_session()
        db_listener = self.repositories.listener.get(session, id=id)
        if not db_listener:
            LOG.info(_LI("Listener %s not found.") % id)
            raise exceptions.NotFound(
                resource=data_models.Listener._name(), id=id)
        # Verify load balancer is in a mutable status.  If so it can be assumed
        # that the listener is also in a mutable status because a load balancer
        # will only be ACTIVE when all it's listeners as ACTIVE.
        self._test_lb_status_put(session, id)
        try:
            LOG.info(_LI("Sending Update of Listener %s to handler") % id)
            self.handler.update(db_listener, listener)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    session, id, provisioning_status=constants.ERROR)
        db_listener = self.repositories.listener.get(session, id=id)
        return self._convert_db_to_type(db_listener,
                                        listener_types.ListenerResponse)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def delete(self, id):
        """Deletes a listener from a load balancer."""
        session = db_api.get_session()
        db_listener = self.repositories.listener.get(session, id=id)
        if not db_listener:
            LOG.info(_LI("Listener %s not found.") % id)
            raise exceptions.NotFound(
                resource=data_models.Listener._name(), id=id)
        # Verify load balancer is in a mutable status.  If so it can be assumed
        # that the listener is also in a mutable status because a load balancer
        # will only be ACTIVE when all it's listeners as ACTIVE.
        if not self.repositories.test_and_set_lb_and_listener_prov_status(
                session, self.load_balancer_id, id, constants.PENDING_UPDATE,
                constants.PENDING_DELETE):
            lb_repo = self.repositories.load_balancer
            db_lb = lb_repo.get(session, id=self.load_balancer_id)
            raise exceptions.ImmutableObject(resource=db_lb._name(),
                                             id=self.load_balancer_id)
        db_listener = self.repositories.listener.get(session, id=id)
        try:
            LOG.info(_LI("Sending Deletion of Listener %s to handler") %
                     db_listener.id)
            self.handler.delete(db_listener)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    session, db_listener.id,
                    provisioning_status=constants.ERROR)
        db_listener = self.repositories.listener.get(
            session, id=db_listener.id)
        return self._convert_db_to_type(db_listener,
                                        listener_types.ListenerResponse)

    @pecan.expose()
    def _lookup(self, listener_id, *remainder):
        """Overriden pecan _lookup method for custom routing.

        Verifies that the listener passed in the url exists, and if so decides
        which controller, if any, should control be passed.
        """
        session = db_api.get_session()
        if listener_id and len(remainder) and remainder[0] == 'pools':
            remainder = remainder[1:]
            db_listener = self.repositories.listener.get(
                session, id=listener_id)
            if not db_listener:
                LOG.info(_LI("Listener %s not found.") % listener_id)
                raise exceptions.NotFound(
                    resource=data_models.Listener._name(), id=listener_id)
            return pool.PoolsController(load_balancer_id=self.load_balancer_id,
                                        listener_id=db_listener.id), remainder
