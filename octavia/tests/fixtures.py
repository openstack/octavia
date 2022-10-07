# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import warnings

import fixtures
from sqlalchemy import exc as sqla_exc


class WarningsFixture(fixtures.Fixture):
    """Filters out warnings during test runs."""

    def setUp(self):
        super().setUp()
        # Make deprecation warnings only happen once to avoid spamming
        warnings.simplefilter('once', DeprecationWarning)

        # Enable deprecation warnings to capture upcoming SQLAlchemy changes
        warnings.filterwarnings(
            'error',
            category=sqla_exc.SADeprecationWarning)

        warnings.filterwarnings(
            'ignore',
            message='The Session.begin.subtransactions flag is deprecated ',
            category=sqla_exc.SADeprecationWarning)

        warnings.filterwarnings(
            'ignore',
            message='The Session.autocommit parameter is deprecated ',
            category=sqla_exc.SADeprecationWarning)

        warnings.filterwarnings(
            'ignore',
            message='The current statement is being autocommitted ',
            category=sqla_exc.SADeprecationWarning)

        warnings.filterwarnings(
            'ignore',
            message='.* object is being merged into a Session along the ',
            category=sqla_exc.SADeprecationWarning)

        warnings.filterwarnings(
            'ignore',
            message='Using plain strings to indicate SQL statements without ',
            category=sqla_exc.SADeprecationWarning)

        warnings.filterwarnings(
            'ignore',
            message='Using non-integer/slice indices on Row is deprecated ',
            category=sqla_exc.SADeprecationWarning)

        warnings.filterwarnings(
            'ignore',
            message='Implicit coercion of SELECT and textual SELECT ',
            category=sqla_exc.SADeprecationWarning)

        warnings.filterwarnings(
            'ignore',
            message='The create_engine.convert_unicode parameter and ',
            category=sqla_exc.SADeprecationWarning)

        self.addCleanup(warnings.resetwarnings)
