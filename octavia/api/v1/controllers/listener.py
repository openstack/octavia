#    Copyright 2014 Rackspace
#    Copyright 2016 Blue Box, an IBM Company
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
from octavia.api.v1.controllers import l7policy
from octavia.api.v1.controllers import listener_statistics
from octavia.api.v1.controllers import pool
from octavia.api.v1.types import listener as listener_types
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.db import prepare as db_prepare
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

    def _get_db_listener(self, session, id):
        """Gets a listener object from the database."""
        db_listener = self.repositories.listener.get(
            session, load_balancer_id=self.load_balancer_id, id=id)
        if not db_listener:
            LOG.info(_LI("Listener %s not found."), id)
            raise exceptions.NotFound(
                resource=data_models.Listener._name(), id=id)
        return db_listener

    @wsme_pecan.wsexpose(listener_types.ListenerResponse, wtypes.text)
    def get_one(self, id):
        """Gets a single listener's details."""
        context = pecan.request.context.get('octavia_context')
        db_listener = self._get_db_listener(context.session, id)
        return self._convert_db_to_type(db_listener,
                                        listener_types.ListenerResponse)

    @wsme_pecan.wsexpose([listener_types.ListenerResponse])
    def get_all(self):
        """Lists all listeners on a load balancer."""
        context = pecan.request.context.get('octavia_context')
        db_listeners = self.repositories.listener.get_all(
            context.session, load_balancer_id=self.load_balancer_id)
        return self._convert_db_to_type(db_listeners,
                                        [listener_types.ListenerResponse])

    def _test_lb_and_listener_statuses(
            self, session, id=None, listener_status=constants.PENDING_UPDATE):
        """Verify load balancer is in a mutable state."""
        lb_repo = self.repositories.load_balancer
        if id:
            if not self.repositories.test_and_set_lb_and_listeners_prov_status(
                    session, self.load_balancer_id, constants.PENDING_UPDATE,
                    listener_status, listener_ids=[id]):
                LOG.info(_LI("Load Balancer %s is immutable."),
                         self.load_balancer_id)
                db_lb = lb_repo.get(session, id=self.load_balancer_id)
                raise exceptions.ImmutableObject(resource=db_lb._name(),
                                                 id=self.load_balancer_id)
        else:
            if not lb_repo.test_and_set_provisioning_status(
                    session, self.load_balancer_id, constants.PENDING_UPDATE):
                db_lb = lb_repo.get(session, id=self.load_balancer_id)
                LOG.info(_LI("Load Balancer %s is immutable."), db_lb.id)
                raise exceptions.ImmutableObject(resource=db_lb._name(),
                                                 id=self.load_balancer_id)

    def _validate_pool(self, session, pool_id):
        """Validate pool given exists on same load balancer as listener."""
        db_pool = self.repositories.pool.get(
            session, load_balancer_id=self.load_balancer_id, id=pool_id)
        if not db_pool:
            raise exceptions.NotFound(
                resource=data_models.Pool._name(), id=pool_id)

    def _validate_listener(self, session, listener_dict):
        """Validate listener for wrong protocol or duplicate listeners

        Update the load balancer db when provisioning status changes.
        """
        lb_repo = self.repositories.load_balancer
        try:
            sni_containers = listener_dict.pop('sni_containers', [])
            db_listener = self.repositories.listener.create(
                session, **listener_dict)
            if sni_containers:
                for container in sni_containers:
                    sni_dict = {'listener_id': db_listener.id,
                                'tls_container_id': container.get(
                                    'tls_container_id')}
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
            LOG.info(_LI("Sending Creation of Listener %s to handler"),
                     db_listener.id)
            self.handler.create(db_listener)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    session, db_listener.id,
                    provisioning_status=constants.ERROR)
        db_listener = self._get_db_listener(session, db_listener.id)
        return self._convert_db_to_type(db_listener,
                                        listener_types.ListenerResponse)

    @wsme_pecan.wsexpose(listener_types.ListenerResponse,
                         body=listener_types.ListenerPOST, status_code=202)
    def post(self, listener):
        """Creates a listener on a load balancer."""
        self._secure_data(listener)
        context = pecan.request.context.get('octavia_context')
        listener_dict = db_prepare.create_listener(
            listener.to_dict(render_unsets=True), self.load_balancer_id)
        if listener_dict['default_pool_id']:
            self._validate_pool(context.session,
                                listener_dict['default_pool_id'])
        self._test_lb_and_listener_statuses(context.session)
        # NOTE(blogan): Throwing away because we should not store secure data
        # in the database nor should we send it to a handler.
        if 'tls_termination' in listener_dict:
            del listener_dict['tls_termination']
        # This is the extra validation layer for wrong protocol or duplicate
        # listeners on the same load balancer.
        return self._validate_listener(context.session, listener_dict)

    @wsme_pecan.wsexpose(listener_types.ListenerResponse, wtypes.text,
                         body=listener_types.ListenerPUT, status_code=202)
    def put(self, id, listener):
        """Updates a listener on a load balancer."""
        self._secure_data(listener)
        context = pecan.request.context.get('octavia_context')
        db_listener = self._get_db_listener(context.session, id)
        listener_dict = listener.to_dict()
        if listener_dict.get('default_pool_id'):
            self._validate_pool(context.session,
                                listener_dict['default_pool_id'])
        self._test_lb_and_listener_statuses(context.session, id=id)

        try:
            LOG.info(_LI("Sending Update of Listener %s to handler"), id)
            self.handler.update(db_listener, listener)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    context.session, id, provisioning_status=constants.ERROR)
        db_listener = self._get_db_listener(context.session, id)
        return self._convert_db_to_type(db_listener,
                                        listener_types.ListenerResponse)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=202)
    def delete(self, id):
        """Deletes a listener from a load balancer."""
        context = pecan.request.context.get('octavia_context')
        db_listener = self._get_db_listener(context.session, id)
        self._test_lb_and_listener_statuses(
            context.session, id=id, listener_status=constants.PENDING_DELETE)

        try:
            LOG.info(_LI("Sending Deletion of Listener %s to handler"),
                     db_listener.id)
            self.handler.delete(db_listener)
        except Exception:
            with excutils.save_and_reraise_exception(reraise=False):
                self.repositories.listener.update(
                    context.session, db_listener.id,
                    provisioning_status=constants.ERROR)
        db_listener = self.repositories.listener.get(
            context.session, id=db_listener.id)
        return self._convert_db_to_type(db_listener,
                                        listener_types.ListenerResponse)

    @pecan.expose()
    def _lookup(self, listener_id, *remainder):
        """Overriden pecan _lookup method for custom routing.

        Verifies that the listener passed in the url exists, and if so decides
        which controller, if any, should control be passed.
        """
        context = pecan.request.context.get('octavia_context')
        if listener_id and len(remainder) and (remainder[0] == 'pools' or
                                               remainder[0] == 'l7policies' or
                                               remainder[0] == 'stats'):
            controller = remainder[0]
            remainder = remainder[1:]
            db_listener = self.repositories.listener.get(
                context.session, id=listener_id)
            if not db_listener:
                LOG.info(_LI("Listener %s not found."), listener_id)
                raise exceptions.NotFound(
                    resource=data_models.Listener._name(), id=listener_id)
            if controller == 'pools':
                return pool.PoolsController(
                    load_balancer_id=self.load_balancer_id,
                    listener_id=db_listener.id), remainder
            elif controller == 'l7policies':
                return l7policy.L7PolicyController(
                    load_balancer_id=self.load_balancer_id,
                    listener_id=db_listener.id), remainder
            elif controller == 'stats':
                return listener_statistics.ListenerStatisticsController(
                    listener_id=db_listener.id), remainder
