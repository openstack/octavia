# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import glob

import docutils.core
from docutils.parsers import rst
from docutils.parsers.rst import directives
import testtools


class FakeDirective(rst.Directive):
    has_content = True

    def run(self):
        return []


directives.register_directive('seqdiag', FakeDirective)
directives.register_directive('blockdiag', FakeDirective)
directives.register_directive('nwdiag', FakeDirective)
directives.register_directive('actdiag', FakeDirective)
directives.register_directive('graphviz', FakeDirective)


class TestTitles(testtools.TestCase):
    def _get_title(self, section_tree):
        section = {
            'subtitles': [],
        }
        for node in section_tree:
            if node.tagname == 'title':
                section['name'] = node.rawsource
            elif node.tagname == 'section':
                subsection = self._get_title(node)
                section['subtitles'].append(subsection['name'])
        return section

    def _get_titles(self, spec):
        titles = {}
        for node in spec:
            if node.tagname == 'section':
                section = self._get_title(node)
                titles[section['name']] = section['subtitles']
        return titles

    def _check_titles(self, titles):
        self.assertEqual(7, len(titles))

        problem = 'Problem description'
        self.assertIn(problem, titles)
        self.assertEqual(0, len(titles[problem]))

        proposed = 'Proposed change'
        self.assertIn(proposed, titles)
        self.assertIn('Alternatives', titles[proposed])
        self.assertIn('Data model impact', titles[proposed])
        self.assertIn('REST API impact', titles[proposed])
        self.assertIn('Security impact', titles[proposed])
        self.assertIn('Notifications impact', titles[proposed])
        self.assertIn('Other end user impact', titles[proposed])
        self.assertIn('Performance Impact', titles[proposed])
        self.assertIn('Other deployer impact', titles[proposed])
        self.assertIn('Developer impact', titles[proposed])

        impl = 'Implementation'
        self.assertIn(impl, titles)
        self.assertEqual(2, len(titles[impl]))
        self.assertIn('Assignee(s)', titles[impl])
        self.assertIn('Work Items', titles[impl])

        deps = 'Dependencies'
        self.assertIn(deps, titles)
        self.assertEqual(0, len(titles[deps]))

        testing = 'Testing'
        self.assertIn(testing, titles)
        self.assertEqual(0, len(titles[testing]))

        docs = 'Documentation Impact'
        self.assertIn(docs, titles)
        self.assertEqual(0, len(titles[docs]))

        refs = 'References'
        self.assertIn(refs, titles)
        self.assertEqual(0, len(titles[refs]))

    def test_template(self):
        files = set(glob.glob('specs/*.rst') + glob.glob('specs/*/*'))
        files = files - set(glob.glob('specs/*/*.dot'))
        files = files - set(glob.glob('specs/*/*.diag'))
        for filename in files:
            self.assertTrue(filename.endswith(".rst"),
                            "spec's file must use 'rst' extension.")
            with open(filename) as f:
                data = f.read()
            spec = docutils.core.publish_doctree(data)
            titles = self._get_titles(spec)
            self._check_titles(titles)
