# Copyright 2014 Rackspace
# All Rights Reserved.
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

from webob import exc


def check_exception(response):
    status_code = response.status_code
    responses = {
        401: Unauthorized,
        403: InvalidRequest,
        404: NotFound,
        405: InvalidRequest,
        409: Conflict,
        500: InternalServerError,
        503: ServiceUnavailable
    }
    if status_code in responses:
        raise responses[status_code]()

    return response


class APIException(exc.HTTPClientError):
    msg = "Something unknown went wrong"
    code = 500

    def __init__(self, **kwargs):
        self.msg = self.msg % kwargs
        super(APIException, self).__init__(detail=self.msg)


class Unauthorized(APIException):
    msg = "Unauthorized"
    code = 401


class InvalidRequest(APIException):
    msg = "Invalid request"
    code = 403


class NotFound(APIException):
    msg = "Not Found"
    code = 404


class Conflict(APIException):
    msg = "Conflict"
    code = 409


class InternalServerError(APIException):
    msg = "Internal Server Error"
    code = 500


class ServiceUnavailable(APIException):
    msg = "Service Unavailable"
    code = 503