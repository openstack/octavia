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

"""WSGI application entry-point for the Octavia API."""

from pathlib import Path
from sys import argv
import threading

from octavia.api import app

application = None
args = None

# Our wsgi app will pull in the sys.argv if we don't pass an argv parameter
# which means octavia will try to use the sphinx-build parameters for oslo
# config. Work around this while maintaining compatiblity by passing the 'h'
# help parameter if we are "running" under sphinx-build.
if Path(argv[0]).name == "sphinx-build":
    args = ['h']

lock = threading.Lock()
with lock:
    if application is None:
        application = app.setup_app(argv=args)
