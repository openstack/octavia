#!/usr/bin/env python
# Copyright 2016 Hewlett Packard Enterprise Development Company LP
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

import argparse
import importlib
import os

import graphviz
from taskflow import engines

from octavia.common import constants
from octavia.tests.common import data_model_helpers as dmh


def main():
    arg_parser = argparse.ArgumentParser(
        description='Generate graphviz representations of the '
                    'Octavia TaskFlow flows.')
    arg_parser.add_argument('-f', '--flow-list', required=True,
                            help='Path to flow list file')
    arg_parser.add_argument('-o', '--output-directory', required=True,
                            help='Path to flow list file')
    args = arg_parser.parse_args()
    generate(args.flow_list, args.output_directory)


def generate(flow_list, output_directory):
    # Create the diagrams
    base_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             os.path.pardir)
    diagram_list = []
    with open(os.path.join(base_path, flow_list), 'r') as flowlist:
        for row in flowlist:
            if row.startswith('#'):
                continue
            current_tuple = tuple(row.strip().split(' '))
            current_class = getattr(importlib.import_module(current_tuple[0]),
                                    current_tuple[1])
            current_instance = current_class()
            get_flow_method = getattr(current_instance, current_tuple[2])
            if (current_tuple[1] == 'AmphoraFlows' and
                    current_tuple[2] == 'get_failover_flow'):
                amp1 = dmh.generate_amphora()
                amp2 = dmh.generate_amphora()
                lb = dmh.generate_load_balancer(amphorae=[amp1, amp2])
                current_engine = engines.load(
                    get_flow_method(role=constants.ROLE_STANDALONE,
                                    load_balancer=lb))
            elif (current_tuple[1] == 'LoadBalancerFlows' and
                  current_tuple[2] == 'get_create_load_balancer_flow'):
                current_engine = engines.load(
                    get_flow_method(
                        constants.TOPOLOGY_ACTIVE_STANDBY))
            elif (current_tuple[1] == 'LoadBalancerFlows' and
                  current_tuple[2] == 'get_delete_load_balancer_flow'):
                lb = dmh.generate_load_balancer()
                delete_flow, store = get_flow_method(lb)
                current_engine = engines.load(delete_flow)
            elif (current_tuple[1] == 'LoadBalancerFlows' and
                  current_tuple[2] == 'get_cascade_delete_load_balancer_flow'):
                lb = dmh.generate_load_balancer()
                delete_flow, store = get_flow_method(lb)
                current_engine = engines.load(delete_flow)
            elif (current_tuple[1] == 'MemberFlows' and
                  current_tuple[2] == 'get_batch_update_members_flow'):
                current_engine = engines.load(
                    get_flow_method([], [], []))
            else:
                current_engine = engines.load(get_flow_method())
            current_engine.compile()
            # We need to render svg and not dot here so we can scale
            # the image in the restructured text page
            src = graphviz.Source(current_engine.compilation.
                                  execution_graph.export_to_dot())
            src.format = 'svg'
            src.render(filename=current_tuple[1] + '-' + current_tuple[2],
                       directory=os.path.join(base_path, output_directory),
                       cleanup=True)
            diagram_list.append((current_tuple[1], current_tuple[2]))

    # Create the class docs
    diagram_list = sorted(diagram_list, key=getDiagKey)
    class_tracker = None
    current_doc_file = None
    for doc_tuple in diagram_list:
        # If we are still working on the same class, append
        if doc_tuple[0] == class_tracker:
            current_doc_file.write('\n')
            current_doc_file.write(doc_tuple[1] + '\n')
            current_doc_file.write('-' * len(doc_tuple[1]) + '\n')
            current_doc_file.write('\n')
            current_doc_file.write('.. only:: html\n')
            current_doc_file.write('\n')
            current_doc_file.write('   .. image:: ' + doc_tuple[0] +
                                   '-' + doc_tuple[1] + '.svg\n')
            current_doc_file.write('       :width: 660px\n')
            current_doc_file.write('       :target: ../../../_images/' +
                                   doc_tuple[0] +
                                   '-' + doc_tuple[1] + '.svg\n')
            current_doc_file.write('\n')
            current_doc_file.write('.. only:: latex\n')
            current_doc_file.write('\n')
            current_doc_file.write('   .. image:: ' + doc_tuple[0] +
                                   '-' + doc_tuple[1] + '.svg\n')
            current_doc_file.write('       :width: 660px\n')

        # First or new class, create the file
        else:
            if current_doc_file is not None:
                current_doc_file.close()
            current_doc_file = open(os.path.join(
                base_path, output_directory, doc_tuple[0] + '.rst'), 'w+')
            class_tracker = doc_tuple[0]

            file_title = constants.FLOW_DOC_TITLES.get(doc_tuple[0],
                                                       'Unknown Flows')

            current_doc_file.write('=' * len(file_title) + '\n')
            current_doc_file.write(file_title + '\n')
            current_doc_file.write('=' * len(file_title) + '\n')
            current_doc_file.write('\n')
            current_doc_file.write('.. contents::\n')
            current_doc_file.write('   :depth: 2\n')
            current_doc_file.write('   :backlinks: top\n')
            current_doc_file.write('\n')
            current_doc_file.write('.. only:: html\n')
            current_doc_file.write('\n')
            current_doc_file.write('   Click on any flow to view full size.\n')
            current_doc_file.write('\n')
            current_doc_file.write(doc_tuple[1] + '\n')
            current_doc_file.write('-' * len(doc_tuple[1]) + '\n')
            current_doc_file.write('\n')
            current_doc_file.write('.. only:: html\n')
            current_doc_file.write('\n')
            current_doc_file.write('   .. image:: ' + doc_tuple[0] +
                                   '-' + doc_tuple[1] + '.svg\n')
            current_doc_file.write('       :width: 660px\n')
            current_doc_file.write('       :target: ../../../_images/' +
                                   doc_tuple[0] +
                                   '-' + doc_tuple[1] + '.svg\n')
            current_doc_file.write('\n')
            current_doc_file.write('.. only:: latex\n')
            current_doc_file.write('\n')
            current_doc_file.write('   .. image:: ' + doc_tuple[0] +
                                   '-' + doc_tuple[1] + '.svg\n')
            current_doc_file.write('       :width: 660px\n')

    current_doc_file.close()


def getDiagKey(item):
    return item[0] + '-' + item[1]


if __name__ == "__main__":
    main()
