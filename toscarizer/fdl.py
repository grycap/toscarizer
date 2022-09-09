import yaml
import json
from toscarizer.utils import RESOURCES_COMPLETE_FILE, BASE_DAG_FILE, parse_dag, parse_resources

def get_oscar_service_json(properties):
    """Get the OSCAR service json"""
    res = {}

    for prop, value in properties.items():
        if value not in [None, [], {}]:
            if prop in ['name', 'script', 'alpine', 'input', 'output', 'storage_providers', 'image', 'memory']:
                res[prop] = value
            elif prop== 'cpu':
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

    for tosca_file in tosca_files:
        with open(tosca_file) as f:
            tosca = yaml.safe_load(f)
            for node_name, node in tosca["topology_template"]["node_templates"].items():
                if node["type"] == "tosca.nodes.aisprint.FaaS.Function":
                    service = get_oscar_service_json(node["properties"])
                    fdl["functions"]["oscar"].append({node_name: service})

    return fdl