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

"""Policy Engine For Octavia."""

import logging

from oslo_config import cfg
from oslo_policy import policy as oslo_policy
from oslo_utils import excutils

from octavia.common import exceptions
from octavia.i18n import _LE
from octavia import policies


LOG = logging.getLogger(__name__)


class Policy(oslo_policy.Enforcer):

    def __init__(self, context, conf=cfg.CONF, policy_file=None, rules=None,
                 default_rule=None, use_conf=True, overwrite=True):
        """Init an Enforcer class.

            :param context: A context object.
            :param conf: A configuration object.
            :param policy_file: Custom policy file to use, if none is
                                specified, ``conf.oslo_policy.policy_file``
                                will be used.
            :param rules: Default dictionary / Rules to use. It will be
                          considered just in the first instantiation. If
                          :meth:`load_rules` with ``force_reload=True``,
                          :meth:`clear` or :meth:`set_rules` with
                          ``overwrite=True`` is called this will be
                          overwritten.
            :param default_rule: Default rule to use, conf.default_rule will
                                 be used if none is specified.
            :param use_conf: Whether to load rules from cache or config file.
            :param overwrite: Whether to overwrite existing rules when reload
                              rules from config file.
        """

        super(Policy, self).__init__(conf, policy_file, rules, default_rule,
                                     use_conf, overwrite)
        self.context = context
        self.register_defaults(policies.list_rules())

    def authorize(self, action, target, do_raise=True, exc=None):
        """Verifies that the action is valid on the target in this context.

           :param context: nova context
           :param action: string representing the action to be checked
               this should be colon separated for clarity.
               i.e. ``compute:create_instance``,
               ``compute:attach_volume``,
               ``volume:attach_volume``
           :param target: dictionary representing the object of the action
               for object creation this should be a dictionary representing the
               location of the object e.g.
               ``{'project_id': context.project_id}``
           :param do_raise: if True (the default), raises PolicyNotAuthorized;
               if False, returns False
           :param exc: Class of the exceptions to raise if the check fails.
                       Any remaining arguments passed to :meth:`enforce` (both
                       positional and keyword arguments) will be passed to
                       the exceptions class. If not specified,
                       :class:`PolicyNotAuthorized` will be used.

           :raises nova.exceptions.PolicyNotAuthorized: if verification fails
               and do_raise is True. Or if 'exc' is specified it will raise an
               exceptions of that type.

           :return: returns a non-False value (not necessarily "True") if
               authorized, and the exact value False if not authorized and
               do_raise is False.
        """
        credentials = self.context.to_policy_values()
        if not exc:
            exc = exceptions.NotAuthorized

        try:
            return super(Policy, self).authorize(
                action, target, credentials, do_raise=do_raise, exc=exc)
        except oslo_policy.PolicyNotRegistered:
            with excutils.save_and_reraise_exception():
                LOG.exception(_LE('Policy not registered'))
        except Exception:
            credentials.pop('auth_token', None)
            with excutils.save_and_reraise_exception():
                LOG.debug('Policy check for %(action)s failed with '
                          'credentials %(credentials)s',
                          {'action': action, 'credentials': credentials})

    def check_is_admin(self):
        """Does roles contains 'admin' role according to policy setting.

        """
        credentials = self.context.to_dict()
        target = credentials
        return self.enforce('context_is_admin', target, credentials)

    def get_rules(self):
        return self.rules


@oslo_policy.register('is_admin')
class IsAdminCheck(oslo_policy.Check):
    """An explicit check for is_admin."""

    def __init__(self, kind, match):
        """Initialize the check."""

        self.expected = match.lower() == 'true'

        super(IsAdminCheck, self).__init__(kind, str(self.expected))

    def __call__(self, target, creds, enforcer):
        """Determine whether is_admin matches the requested value."""

        return creds['is_admin'] == self.expected
