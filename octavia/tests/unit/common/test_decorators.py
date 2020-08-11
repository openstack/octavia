#    Copyright 2016
#    All Rights Reserved.
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


"""Test for the decorator which provides backward compatibility for V1 API."""

import octavia.common.decorators as dec
import octavia.tests.unit.base as base


class TestDecorator(base.TestCase):

    @dec.rename_kwargs(a='z')
    class TestClass(object):
        def __init__(self, x, z=None):
            self.x = x
            self.z = z

    @dec.rename_kwargs(a='z')
    class TestClassDupe(object):
        def __init__(self, x, z=None):
            self.x = x
            self.z = z

    def test_get(self):
        obj = self.TestClass(1, a=3)
        self.assertEqual(1, obj.x)
        self.assertEqual(3, obj.z)
        self.assertEqual(obj.z, obj.a)

    def test_set(self):
        obj = self.TestClass(1, a=3)
        obj.a = 5
        self.assertEqual(1, obj.x)
        self.assertEqual(5, obj.z)
        self.assertEqual(obj.z, obj.a)

    def test_similar_classes(self):
        obj = self.TestClass(1, z=5)
        obj2 = self.TestClassDupe(2, z=10)
        self.assertEqual(5, obj.z)
        self.assertEqual(10, obj2.z)
        self.assertEqual(obj.z, obj.a)
        self.assertEqual(obj2.z, obj2.a)
