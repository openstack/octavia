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

import contextlib

from oslo_config import cfg
from oslo_db.sqlalchemy import session as db_session
from oslo_utils import excutils

_FACADE = None


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = db_session.EngineFacade.from_config(cfg.CONF, sqlite_fk=True)
    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(expire_on_commit=True, autocommit=True):
    """Helper method to grab session."""
    facade = _create_facade_lazily()
    return facade.get_session(expire_on_commit=expire_on_commit,
                              autocommit=autocommit)


@contextlib.contextmanager
def get_lock_session():
    """Context manager for using a locking (not auto-commit) session."""
    lock_session = get_session(autocommit=False)
    try:
        yield lock_session
        lock_session.commit()
    except Exception:
        with excutils.save_and_reraise_exception():
            lock_session.rollback()
