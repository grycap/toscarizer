# Copyright (C) GRyCAP - I3M - UPV
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import yaml


def get_oscar_service_json(properties):
    """Get the OSCAR service json"""
    res = {}

    for prop, value in properties.items():
        if value not in [None, [], {}]:
            if prop in ['name', 'script', 'alpine', 'input', 'output', 'storage_providers', 'image', 'memory']:
                res[prop] = value
            elif prop == 'cpu':
                res['cpu'] = "%g" % value
            elif prop == 'env_variables':
                res['environment'] = {'Variables': value}
            elif prop == 'image_pull_secrets':
                if not isinstance(value, list):
                    value = [value]
                res['image_pull_secrets'] = value

    return res


def generate_fdl(tosca_files):
    fdl = {"functions": {"oscar": []}}

    done = []
    for tosca_file in tosca_files:
        if "infras.yaml" not in tosca_file:
            with open(tosca_file) as f:
                tosca = yaml.safe_load(f)
                oscar_name = None
                # Name in already deployed cluster
                if "oscar_name" in tosca["topology_template"]["inputs"]:
                    oscar_name = tosca["topology_template"]["inputs"]["oscar_name"]["default"]
                # Name in IM generated cluster
                elif "cluster_name" in tosca["topology_template"]["inputs"]:
                    oscar_name = tosca["topology_template"]["inputs"]["cluster_name"]["default"]
                for node_name, node in tosca["topology_template"]["node_templates"].items():
                    if node["type"] == "tosca.nodes.aisprint.FaaS.Function":
                        service = get_oscar_service_json(node["properties"])
                        if service["name"] not in done:
                            cluster_name = oscar_name if oscar_name else node_name
                            fdl["functions"]["oscar"].append({cluster_name: service})
                            done.append(service["name"])

    return fdl
