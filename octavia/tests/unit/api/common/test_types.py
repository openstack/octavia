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

from wsme import types as wtypes

from octavia.api.common import types
from octavia.db import base_models
from octavia.tests.unit import base


class TestTypeRename(types.BaseType):
    _type_to_db_map = {'renamed': 'original',
                       'child_one': 'child.one',
                       'child_two': 'child.two',
                       'admin_state_up': 'enabled'}
    id = wtypes.wsattr(wtypes.StringType())
    renamed = wtypes.wsattr(wtypes.StringType())
    child_one = wtypes.wsattr(wtypes.StringType())
    child_two = wtypes.wsattr(wtypes.StringType())
    admin_state_up = wtypes.wsattr(bool)

    @classmethod
    def from_db_obj(cls, db_obj):
        result = super().from_db_obj(db_obj)

        if db_obj.child:
            result.child_one = db_obj.child.one
            result.child_two = db_obj.child.two

        return result


class TestTypeRenameSubset(types.BaseType):
    _type_to_db_map = {'renamed': 'original',
                       'child_one': 'child.one',
                       'child_two': 'child.two'}
    id = wtypes.wsattr(wtypes.StringType())
    renamed = wtypes.wsattr(wtypes.StringType())


class TestTypeTenantProject(types.BaseType):
    tenant_id = wtypes.wsattr(wtypes.StringType())
    project_id = wtypes.wsattr(wtypes.StringType())


class ChildTestDbObj(base_models.OctaviaBase):

    def __init__(self, one=None, two=None):
        self.one = one
        self.two = two


class TestDbObj(base_models.OctaviaBase):

    def __init__(self, id=None, original=None, child=None, enabled=None):
        self.id = id
        self.original = original
        self.child = child
        self.enabled = enabled


class TestTypeDbObjRenames(base.TestCase):

    def setUp(self):
        super().setUp()
        child = ChildTestDbObj(one='baby_turtle_one', two='baby_turtle_two')
        self.db_obj = TestDbObj(id='1234', original='turtles', child=child)

    def test_db_obj_to_type(self):
        new_type = TestTypeRename.from_db_obj(self.db_obj)
        self.assertEqual(self.db_obj.original, new_type.renamed)
        self.assertEqual(self.db_obj.child.one, new_type.child_one)
        self.assertEqual(self.db_obj.child.two, new_type.child_two)
        self.assertEqual(self.db_obj.id, new_type.id)

    def test_db_obj_to_type_with_subset_of_fields(self):
        new_type = TestTypeRenameSubset.from_db_obj(self.db_obj)
        self.assertEqual(self.db_obj.original, new_type.renamed)
        self.assertEqual(self.db_obj.id, new_type.id)
        self.assertFalse(hasattr(new_type, 'child_one'))
        self.assertFalse(hasattr(new_type, 'child_two'))

    def test_type_to_dict(self):
        new_type = TestTypeRename(id='1234', renamed='turtles',
                                  child_one='baby_turtle_one',
                                  child_two='baby_turtle_two')
        type_dict = new_type.to_dict()
        self.assertEqual(new_type.id, type_dict.get('id'))
        self.assertEqual(new_type.renamed, type_dict.get('original'))
        self.assertIn('child', type_dict)
        child_dict = type_dict.pop('child')
        self.assertEqual(new_type.child_one, child_dict.get('one'))
        self.assertEqual(new_type.child_two, child_dict.get('two'))

    def test_translate_dict_keys_to_db_obj(self):
        new_type = TestTypeRename.from_db_obj(self.db_obj)
        new_type_vars = {
            k: getattr(new_type, k) for k in dir(new_type) if not (
                callable(getattr(new_type, k)) or k.startswith('_'))
        }
        self.assertEqual(
            set(vars(self.db_obj)),
            set(new_type.translate_dict_keys_to_db_obj(new_type_vars)),
        )

    def test_type_to_dict_with_tenant_id(self):
        type_dict = TestTypeTenantProject(tenant_id='1234').to_dict()
        self.assertEqual('1234', type_dict['project_id'])
        self.assertNotIn('tenant_id', type_dict)

    def test_type_to_dict_when_admin_state_up_is_null(self):
        rtype = TestTypeRename(id='1234', renamed='turtles',
                               child_one='baby_turtle_one',
                               child_two='baby_turtle_two',
                               admin_state_up=None)
        rtype_dict = rtype.to_dict()
        self.assertFalse(rtype_dict['enabled'])


class TestToDictDbObj(base_models.OctaviaBase):

    def __init__(self, text, parent=None, children=None, child=None):
        self.parent = parent
        self.child = child
        self.children = children
        self.text = text


class TestDbObjToDict(base.TestCase):
    RECURSED_RESULT = {'parent': None,
                       'text': 'parent_text',
                       'child': {'parent': None,
                                 'text': 'child_text',
                                 'child': None,
                                 'children': None},
                       'children': [
                           {'parent': None,
                            'text': 'child1_text',
                            'child': None,
                            'children': None},
                           {'parent': None,
                            'text': 'child2_text',
                            'child': None,
                            'children': None}]}

    NO_RECURSE_RESULT = {'parent': None,
                         'text': 'parent_text',
                         'child': None,
                         'children': []}

    def setUp(self):
        super().setUp()
        self.db_obj = (
            TestToDictDbObj(
                'parent_text',
                children=[
                    TestToDictDbObj('child1_text'),
                    TestToDictDbObj('child2_text')
                ],
                child=TestToDictDbObj('child_text')
            )
        )

    def test_to_dict_no_recurse(self):
        self.assertEqual(self.db_obj.to_dict(),
                         self.NO_RECURSE_RESULT)

    def test_to_dict_recurse(self):
        self.assertEqual(self.db_obj.to_dict(recurse=True),
                         self.RECURSED_RESULT)

    def test_type_to_dict_with_project_id(self):
        type_dict = TestTypeTenantProject(project_id='1234').to_dict()
        self.assertEqual('1234', type_dict['project_id'])
        self.assertNotIn('tenant_id', type_dict)
