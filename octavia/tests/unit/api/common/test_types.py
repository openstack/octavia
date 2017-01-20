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
from octavia.common import data_models
from octavia.tests.unit import base


class TestTypeRename(types.BaseType):
    _type_to_model_map = {'renamed': 'original',
                          'child_one': 'child.one',
                          'child_two': 'child.two'}
    id = wtypes.wsattr(wtypes.StringType())
    renamed = wtypes.wsattr(wtypes.StringType())
    child_one = wtypes.wsattr(wtypes.StringType())
    child_two = wtypes.wsattr(wtypes.StringType())


class TestTypeRenameSubset(types.BaseType):
    _type_to_model_map = {'renamed': 'original',
                          'child_one': 'child.one',
                          'child_two': 'child.two'}
    id = wtypes.wsattr(wtypes.StringType())
    renamed = wtypes.wsattr(wtypes.StringType())


class TestTypeTenantProject(types.BaseType):
    tenant_id = wtypes.wsattr(wtypes.StringType())
    project_id = wtypes.wsattr(wtypes.StringType())


class ChildTestModel(data_models.BaseDataModel):

    def __init__(self, one=None, two=None):
        self.one = one
        self.two = two


class TestModel(data_models.BaseDataModel):

    def __init__(self, id=None, original=None, child=None):
        self.id = id
        self.original = original
        self.child = child

    def to_dict(self):
        result = super(TestModel, self).to_dict()
        result['child'] = self.child.to_dict()
        return result


class TestTypeDataModelRenames(base.TestCase):

    def setUp(self):
        super(TestTypeDataModelRenames, self).setUp()
        child_model = ChildTestModel(one='baby_turtle_one',
                                     two='baby_turtle_two')
        self.model = TestModel(id='1234', original='turtles',
                               child=child_model)

    def test_model_to_type(self):
        new_type = TestTypeRename.from_data_model(self.model)
        self.assertEqual(self.model.original, new_type.renamed)
        self.assertEqual(self.model.child.one, new_type.child_one)
        self.assertEqual(self.model.child.two, new_type.child_two)
        self.assertEqual(self.model.id, new_type.id)

    def test_model_to_type_with_subset_of_fields(self):
        new_type = TestTypeRenameSubset.from_data_model(self.model)
        self.assertEqual(self.model.original, new_type.renamed)
        self.assertEqual(self.model.id, new_type.id)
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

    def test_type_to_dict_with_tenant_id(self):
        type_dict = TestTypeTenantProject(tenant_id='1234').to_dict()
        self.assertEqual('1234', type_dict['project_id'])
        self.assertNotIn('tenant_id', type_dict)


class TestToDictModel(data_models.BaseDataModel):
    def __init__(self, text, parent=None):
        self.parent = parent
        self.child = None
        self.children = None
        self.text = text

    def set_children(self, children):
        self.children = children

    def set_child(self, child):
        self.child = child

    def set_parent(self, parent):
        self.parent = parent


class TestDataModelToDict(base.TestCase):
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
                         'children': None}

    def setUp(self):
        super(TestDataModelToDict, self).setUp()
        self.model = TestToDictModel('parent_text')
        self.model.set_child(TestToDictModel('child_text', self.model))
        self.model.set_children([TestToDictModel('child1_text', self.model),
                                 TestToDictModel('child2_text', self.model)])

    def test_to_dict_no_recurse(self):
        self.assertEqual(self.model.to_dict(),
                         self.NO_RECURSE_RESULT)

    def test_to_dict_recurse(self):
        self.assertEqual(self.model.to_dict(recurse=True),
                         self.RECURSED_RESULT)

    def test_type_to_dict_with_project_id(self):
        type_dict = TestTypeTenantProject(project_id='1234').to_dict()
        self.assertEqual('1234', type_dict['project_id'])
        self.assertNotIn('tenant_id', type_dict)
