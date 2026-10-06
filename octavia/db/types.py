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

"""Custom SQLAlchemy types."""

import sqlalchemy as sa
from sqlalchemy import types


class ScalarListType(types.TypeDecorator):
    """A type for saving a list of strings as a comma-separated string."""

    impl = sa.UnicodeText
    #: Indicate if statements using this type are safe to cache.
    cache_ok = True

    def __init__(self, separator=',', **kwargs):
        self.separator = separator
        super().__init__(**kwargs)

    def process_bind_param(self, value, dialect):
        """Serialize a list of strings to a delimited string."""
        if value is None:
            return None
        if any(self.separator in str(item) for item in value):
            raise ValueError(
                f"List values cannot contain separator {self.separator!r}"
            )
        return self.separator.join(str(item) for item in value)

    def process_result_value(self, value, dialect):
        """Deserialize a delimited string to a list of strings."""
        if value is None:
            return None
        if not value:
            return []
        return value.split(self.separator)
