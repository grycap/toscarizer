import yaml
import copy
import random
import string
import os.path
import re


TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
TOSCA_TEMPLATE = os.path.join(TEMPLATES_PATH, 'oscar.yaml')
WN_TOSCA_TEMPLATE = os.path.join(TEMPLATES_PATH, 'oscar_wn.yaml')
ELASTIC_TOSCA_TEMPLATE = os.path.join(TEMPLATES_PATH, 'oscar_elastic.yaml')
ELASTIC_WN_TOSCA_TEMPLATE = os.path.join(TEMPLATES_PATH, 'oscar_wn_elastic.yaml')


def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase + string.digits
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


def gen_oscar_name():
    # TODO: https://github.com/grycap/im-dashboard/blob/master/app/utils.py#L435
    return "oscar-cluster-%s" % get_random_string(8)


def merge_templates(template, new_template):
    for item in ["inputs", "node_templates", "outputs"]:
        if item in new_template["topology_template"]:
            if item not in template["topology_template"]:
                template["topology_template"][item] = {}
            template["topology_template"][item].update(new_template["topology_template"][item])
    return template


def find_compute_layer(resources, component_name, components):
    component = None
    for c in list(components.values()):
        if c["name"] == component_name:
            component = c
            break
    if not component:
        raise Exception("No component named %s found." % component_name)
    layer_num = component.get("executionLayer")
    if not layer_num:
        layer_num = component["candidateExecutionLayers"][0]
    for nd in list(resources["NetworkDomains"].values()):
        if "ComputationalLayers" in nd:
            for cl_name, cl in nd["ComputationalLayers"].items():
                if cl.get("number") == layer_num:
                    cont = list(component["Containers"].values())[0]
                    if "candidateExecutionResources" in cont:
                        res_name = cont["candidateExecutionResources"][0]
                    elif "selectedExecutionResource" in cont:
                        res_name = cont["selectedExecutionResource"]
                    else:
                        raise Exception("No ExecutionResources in container")
                    return res_name, cont, cl_name, layer_num
    return None, None, None, None


def add_nets(tosca_tpl):
    tosca_tpl["topology_template"]["node_templates"]["pub_network"] = {"type": "tosca.nodes.network.Network",
                                                                       "properties": {"network_type": "public"}}

    tosca_tpl["topology_template"]["node_templates"]["priv_network"] = {"type": "tosca.nodes.network.Network",
                                                                        "properties": {"network_type": "private"}}
    return tosca_tpl


def set_ip_details(tosca_tpl, node_name, node_net, ip, order):
    port_name = "%s_%s_port" % (node_name, node_net)
    tosca_tpl["topology_template"]["node_templates"][port_name] = {"type": "tosca.nodes.network.Port",
                                                                   "properties": {
                                                                       "order": order,
                                                                       "ip_address": ip
                                                                   },
                                                                   "requirements": [
                                                                       {"binding": node_name},
                                                                       {"link": node_net}
                                                                   ]}
    return tosca_tpl


def set_node_credentials(node_tpl, username, key):
    node_tpl["capabilities"]["os"]["properties"]["credential"] = {"user": username,
                                                                  "token_type": "private_key",
                                                                  "token": key}


def get_physical_resource_data(comp_layer, res, phys_file, node_type, value, index=None):
    for cl in list(phys_file["ComputationalLayers"].values()):
        if cl["number"] == comp_layer["number"]:
            for r in list(cl["Resources"].values()):
                if r["name"] == res["name"]:
                    try:
                        if index is not None:
                            return r[node_type][index][value]
                        else:
                            return r[node_type][value]
                    except Exception:
                        return None
    return None


def gen_tosca_yamls(app_name, dag, resources_file, deployments_file, phys_file, elastic,
                    auth_data, domain, influxdb_url, influxdb_token, qos_contraints_file,
                    containers_file):
    with open(deployments_file, 'r') as f:
        deployments = yaml.safe_load(f)
        if "System" in deployments:
            deployments = deployments["System"]
    with open(resources_file, 'r') as f:
        full_resouces = yaml.safe_load(f)
        if "System" in full_resouces:
            full_resouces = full_resouces["System"]
        if "Resources" in full_resouces:
            full_resouces = full_resouces["Resources"]

    qos_contraints_by_level = {}
    qos_contraints_full = None
    if os.path.exists(qos_contraints_file):
        with open(qos_contraints_file, 'r') as f:
            qos_contraints_yaml = yaml.safe_load(f)
            qos_contraints_yaml['System']['name'] = qos_contraints_yaml['System']['name'].replace('_', '-')
            qos_contraints_full = yaml.safe_dump(qos_contraints_yaml)
    else:
        path = os.path.dirname(qos_contraints_file)
        for fn in os.listdir(path):
            z = re.match(r"qos_constraints_L(\d+).yaml", fn)
            if z:
                level = int(z.group(1))
                with open(os.path.join(path, fn), 'r') as f:
                    qos_contraints_yaml = yaml.safe_load(f)
                    qos_contraints_yaml['System']['name'] = qos_contraints_yaml['System']['name'].replace('_', '-')
                    qos_contraints_by_level[level] = yaml.safe_dump(qos_contraints_yaml)

    phys_nodes = {}
    if phys_file and os.path.isfile(phys_file):
        with open(phys_file, 'r') as f:
            phys_nodes = yaml.safe_load(f)

    # Get a dict of ComputationalLayers by name
    cls = {}
    for nd in list(full_resouces["NetworkDomains"].values()):
        if "ComputationalLayers" in nd:
            for cl_name, cl in nd["ComputationalLayers"].items():
                cls[cl_name] = cl

    # Create the OSCAR clusters per component
    oscar_clusters_per_component = {}
    container_per_component = {}
    for component in dag.nodes():
        # First find the Component cluster
        res_name, cont, cl_name, num = find_compute_layer(full_resouces, component, deployments["Components"])
        container_per_component[component] = cont
        if not cl_name:
            raise Exception("No compute layer found for component." % component.get("name"))
        # check if there are general qos_contraints by level
        qos_contraints = qos_contraints_by_level.get(num)
        if not qos_contraints:
            # if not use the general one
            qos_contraints = qos_contraints_full
        oscar_clusters_per_component[component] = gen_tosca_cluster(cls[cl_name], num, res_name, phys_nodes,
                                                                    elastic, auth_data, domain, app_name,
                                                                    influxdb_url, influxdb_token, qos_contraints)

    # Gen influx layers
    layers = gen_next_layer_influx(oscar_clusters_per_component)

    # Add drift detector component
    last_layer_cluster = None
    max_layer = max(k for k, v in layers.items() if not v[0].get("aws"))
    drift_detector = get_drift_detector(containers_file,
                                        layers[max_layer][0]["cluster"],
                                        layers[max_layer][0]["component"])
    if drift_detector:
        last_layer_cluster = layers[max_layer][0]["cluster"]
        merge_templates(last_layer_cluster, drift_detector)

    # Now create the OSCAR services and merge in the correct OSCAR cluster
    for component, next_items in dag.adj.items():
        # Add the node
        oscar_service = get_service(app_name, component, next_items, list(dag.predecessors(component)),
                                    container_per_component[component], oscar_clusters_per_component,
                                    last_layer_cluster)
        oscar_clusters_per_component[component] = merge_templates(oscar_clusters_per_component[component],
                                                                  oscar_service)

    to_delete = ["minio_endpoint", "minio_ak", "minio_sk", "oscar_name",
                 "aws", "aws_region", "aws_bucket", "aws_ak", "aws_sk",
                 "influx_endpoint", "influx_token", "layer_num"]
    for cluster in list(oscar_clusters_per_component.values()):
        for item in to_delete:
            if item in cluster["topology_template"]["inputs"]:
                del cluster["topology_template"]["inputs"][item]

    return oscar_clusters_per_component


def gen_next_layer_influx(oscar_clusters):
    layers = {}
    for component, oscar_cluster in oscar_clusters.items():
        cluster_inputs = oscar_cluster["topology_template"]["inputs"]
        curr_cluster_aws = "aws" in cluster_inputs and cluster_inputs["aws"]["default"]
        num = cluster_inputs["layer_num"]["default"]
        if num not in layers:
            layers[num] = []
        layers[num].append({"cluster": oscar_cluster, "aws": curr_cluster_aws, "component": component})
        elem = len(layers[num]) - 1
        if not curr_cluster_aws:
            if len(oscar_cluster["topology_template"]["node_templates"]) > 1:
                layers[num][elem]["endpoint"] = "https://influx.%s.%s" % (cluster_inputs["cluster_name"]["default"],
                                                                          cluster_inputs["domain_name"]["default"])
                layers[num][elem]["token"] = cluster_inputs["local_influx_token"]["default"]
            else:
                if "influx_endpoint" in cluster_inputs and "influx_token" in cluster_inputs:
                    layers[num][elem]["endpoint"] = cluster_inputs["influx_endpoint"]["default"]
                    layers[num][elem]["token"] = cluster_inputs["influx_token"]["default"]

    for num, layer in layers.items():

        next_layer = None
        for next_num in list(layers.keys()):
            if next_num > num and "endpoint" in layers[next_num][0]:
                next_layer = layers[next_num]

        if next_layer:
            for elem in layer:
                cluster_inputs = elem["cluster"]["topology_template"]["inputs"]
                cluster_inputs["top_influx_url"] = {"default": next_layer[0]["endpoint"],
                                                    "type": "string"}
                cluster_inputs["top_influx_token"] = {"default": next_layer[0]["token"],
                                                      "type": "string"}
    return layers


def get_drift_detector(containers_file, oscar_cluster, component):
    """Generate the drift detector TOSCA component."""
    with open(containers_file, 'r') as f:
        containers = yaml.safe_load(f)

    if not containers.get("components", {}).get("drift-detector"):
        return None

    cluster_inputs = oscar_cluster["topology_template"]["inputs"]
    if len(oscar_cluster["topology_template"]["node_templates"]) > 1:
        influx_token = cluster_inputs["local_influx_token"]["default"]
    else:
        raise Exception("Drift detector not supported for already deployed clusters.")

    deployment = {
        "type": "tosca.nodes.indigo.KubernetesObject",
        "requirements": [{"host": "lrms_front_end"}],
        "properties": {
            "spec": """
---
apiVersion: v1
kind: Namespace
metadata:
  name: drift-detector
---
apiVersion: apps/v1
kind: Deployment
metadata:
    name: drift-detector
    namespace: drift-detector
spec:
    replicas: 1
    spec:
        containers:
          - name: drift-detector
            env:
            - name: DRIFT_DETECTOR_INFLUXDB_URL
              value: http://ai-sprint-monit-influxdb.ai-sprint-monitoring:8086
            - name: DRIFT_DETECTOR_INFLUXDB_TOKEN
              value: %s
            - name: COMPONENT_NAME
              value: %s
            - name: DRIFT_DETECTOR_MINIO_FOLDER
              value: drift_detector
            - name: DRIFT_DETECTOR_MINIO_URL
              value: 'http://minio.minio:9000'
            - name: DRIFT_DETECTOR_MINIO_AK
              value: minio
            - name: DRIFT_DETECTOR_MINIO_SK
              value: %s
            value: "Hello from the environment"
            image: %s""" % (influx_token,
                            component,
                            cluster_inputs["minio_password"]["default"],
                            containers["components"]["drift-detector"]["docker_images"][0])
        }
    }

    res = {
            "topology_template":
            {
                "node_templates": {"drift_detector": deployment},
            }
    }

    return res


def get_service(app_name, component, next_items, prev_items, container, oscar_clusters, drift_cluster):
    """Generate the OSCAR service TOSCA."""
    service = {
        "type": "tosca.nodes.aisprint.FaaS.Function",
        "properties": {
            "name": component.replace("_", "-"),
            "image": container.get("image"),
            "script": "/opt/%s/script.sh" % component,
            "input": [],
            "output": [],
            "memory": "%sMi" % container.get("memorySize", 512),
            "cpu": container.get("computingUnits", "1"),
            "env_variables": {
                "COMPONENT_NAME": component,
                "MONIT_HOST": "%s-telegraf" % app_name,
                "MONIT_PORT": "8094"
            }
        }
    }

    cluster_inputs = oscar_clusters[component]["topology_template"]["inputs"]
    curr_cluster_aws = "aws" in cluster_inputs and cluster_inputs["aws"]["default"]
    if len(oscar_clusters[component]["topology_template"]["node_templates"]) > 1:
        # It is a IM deployed cluster
        # Use the minio url as we alredy have it
        service["properties"]["env_variables"]["KCI"] = \
            "https://minio.%s.%s" % (cluster_inputs["cluster_name"]["default"],
                                     cluster_inputs["domain_name"]["default"])
    elif curr_cluster_aws:
        # It is deployed in AWS Lambda
        service["properties"]["env_variables"]["KCI"] = "AWS Lambda"
        service["properties"]["env_variables"]["RESOURCE_ID"] = "AWS Lambda"
        service["properties"]["env_variables"]["MONIT_HOST"] = "localhost"
        service["properties"]["env_variables"]["INFLUX_ENDPOINT"] = cluster_inputs["top_influx_url"]["default"]
        service["properties"]["env_variables"]["INFLUX_TOKEN"] = cluster_inputs["top_influx_token"]["default"]
    else:
        # It is an already existing OSCAR cluster
        service["properties"]["env_variables"]["KCI"] = cluster_inputs["minio_endpoint"]["default"]

    if drift_cluster:
        # There is a drift detector add needed env variables
        drift_cluster_inputs = drift_cluster["topology_template"]["inputs"]
        minio_endpoint = "https://minio.%s.%s" % (drift_cluster_inputs["cluster_name"]["default"],
                                                  drift_cluster_inputs["domain_name"]["default"])

        service["properties"]["env_variables"]["DRIFT_DETECTOR_MINIO_URL"] = minio_endpoint
        service["properties"]["env_variables"]["DRIFT_DETECTOR_MINIO_FOLDER"] = "drift_detector"
        service["properties"]["env_variables"]["DRIFT_DETECTOR_MINIO_AK"] = "minio"
        service["properties"]["env_variables"]["DRIFT_DETECTOR_MINIO_SK"] = \
            drift_cluster_inputs["minio_password"]["default"]

    storage_providers = {}

    # Add inputs (All must be in the local cluster)
    for prev_item in prev_items:
        if curr_cluster_aws:
            service["properties"]["input"].append({
                "storage_provider": "s3",
                "path": "%s/%s/output" % (cluster_inputs["aws_bucket"]["default"],
                                          prev_item.replace("_", "-"))
            })
        else:
            service["properties"]["input"].append({
                "storage_provider": "minio",
                "path": "%s/output" % prev_item.replace("_", "-")
            })

    # Add outputs (check if they are in the same or in other OSCAR cluster)
    for next_comp in next_items:
        if oscar_clusters[component] != oscar_clusters[next_comp]:
            cluster_inputs = oscar_clusters[next_comp]["topology_template"]["inputs"]
            cluster_name = cluster_inputs["cluster_name"]["default"]
            repeated = False
            if cluster_name in storage_providers:
                repeated = True
            if not curr_cluster_aws and "aws" in cluster_inputs and cluster_inputs["aws"]["default"]:
                # The output is for a lambda function but this is not a lambda function
                if not repeated:
                    storage_providers[cluster_name] = {
                        "access_key": cluster_inputs["aws_ak"]["default"],
                        "secret_key": cluster_inputs["aws_sk"]["default"],
                        "region": cluster_inputs["aws_region"]["default"],
                    }
            else:
                if len(oscar_clusters[next_comp]["topology_template"]["node_templates"]) > 1:
                    # It is a IM deployed cluster
                    if not repeated:
                        storage_providers[cluster_name] = {
                            "endpoint": "https://minio.%s.%s" % (cluster_inputs["cluster_name"]["default"],
                                                                 cluster_inputs["domain_name"]["default"]),
                            # "verify": True,
                            "access_key": "minio",
                            "secret_key": cluster_inputs["minio_password"]["default"],
                            "region": "us-east-1"
                        }
                else:
                    # It is an already existing OSCAR cluster
                    if not repeated:
                        storage_providers[cluster_name] = {
                            "endpoint": cluster_inputs["minio_endpoint"]["default"],
                            # "verify": True,
                            "access_key": cluster_inputs["minio_ak"]["default"],
                            "secret_key": cluster_inputs["minio_sk"]["default"],
                            "region": "us-east-1"
                        }

            # avoid adding the same output again
            if not repeated:
                if "aws" in cluster_inputs and cluster_inputs["aws"]["default"]:
                    service["properties"]["output"].append({
                        "storage_provider": "s3.%s" % cluster_name,
                        "path": "%s/%s/output" % (cluster_inputs["aws_bucket"]["default"],
                                                  component.replace("_", "-"))
                    })
                else:
                    service["properties"]["output"].append({
                        "storage_provider": "minio.%s" % cluster_name,
                        "path": "%s/output" % component.replace("_", "-")
                    })

    cluster_inputs = oscar_clusters[component]["topology_template"]["inputs"]
    if not service["properties"]["output"]:
        default_output = {
            "storage_provider": "minio",
            "path": "%s/output" % component.replace("_", "-")
        }
        if curr_cluster_aws:
            default_output = {
                "storage_provider": "s3",
                "path": "%s/%s/output" % (cluster_inputs["aws_bucket"]["default"],
                                          component.replace("_", "-"))
            }
        service["properties"]["output"].append(default_output)

    if not service["properties"]["input"]:
        default_input = {
            "storage_provider": "minio",
            "path": "%s/input" % component.replace("_", "-")
        }
        if curr_cluster_aws:
            default_input = {
                "storage_provider": "s3",
                "path": "%s/%s/input" % (cluster_inputs["aws_bucket"]["default"],
                                         component.replace("_", "-"))
            }
        service["properties"]["input"].append(default_input)

    if len(oscar_clusters[component]["topology_template"]["node_templates"]) > 1:
        service["requirements"] = [
            {"host": "oscar"}
        ]

    if storage_providers:
        service["properties"]["storage_providers"] = {}
        for cl_name, storage in storage_providers.items():
            if "endpoint" in storage:
                # MinIO
                if "minio" not in service["properties"]["storage_providers"]:
                    service["properties"]["storage_providers"]["minio"] = {}
                service["properties"]["storage_providers"]["minio"][cl_name] = storage
            else:
                # AWS
                if "s3" not in service["properties"]["storage_providers"]:
                    service["properties"]["storage_providers"]["s3"] = {}
                service["properties"]["storage_providers"]["s3"][cl_name] = storage

    if "aws" in cluster_inputs and cluster_inputs["aws"]["default"]:
        res = {
                "topology_template":
                {
                    "node_templates": {"lambda_function_%s" % component: service},
                }
        }
    else:
        res = {
                "topology_template":
                {
                    "node_templates": {"oscar_service_%s" % component: service},
                    "outputs": {
                        "oscar_service_url": {"value": {"get_attribute": ["oscar_service_%s" % component,
                                                                          "endpoint"]}},
                        "oscar_service_cred": {"value": {"get_attribute": ["oscar_service_%s" % component,
                                                                           "credential"]}}
                    }
                }
        }

    return res


def gen_tosca_cluster(compute_layer, layer_num, res_name, phys_nodes, elastic, auth_data,
                      domain, app_name, influxdb_url, influxdb_token, qos_constraints):
    with open(TOSCA_TEMPLATE, 'r') as f:
        tosca_tpl = yaml.safe_load(f)

    if elastic:
        with open(ELASTIC_TOSCA_TEMPLATE, 'r') as f:
            elastic_tosca_tpl = yaml.safe_load(f)

        with open(ELASTIC_WN_TOSCA_TEMPLATE, 'r') as f:
            wn_tosca_tpl = yaml.safe_load(f)
    else:
        with open(WN_TOSCA_TEMPLATE, 'r') as f:
            wn_tosca_tpl = yaml.safe_load(f)

    # Default empty TOSCA
    tosca_res = {
        "tosca_definitions_version": "tosca_simple_yaml_1_0",
        "imports": [
            {"ec3_custom_types": "https://raw.githubusercontent.com/grycap/ec3/tosca/tosca/custom_types.yaml"}
        ],
        "topology_template": {
            "node_templates": {},
            "inputs": {
                "cluster_name": {
                    "default": gen_oscar_name(),
                    "type": "string"
                },
                "layer_num": {
                    "default": layer_num,
                    "type": "integer"
                }
            }
        }
    }

    if compute_layer["type"] in ["Virtual", "PhysicalToBeProvisioned"]:
        tosca_comp = copy.deepcopy(tosca_tpl)
        if elastic:
            tosca_comp["topology_template"]["node_templates"].update(elastic_tosca_tpl)
            tosca_comp["topology_template"]["inputs"]["max_wn_num"]["default"] = elastic
            ec_fe = tosca_comp["topology_template"]["node_templates"]["elastic_cluster_front_end"]
            ec_fe["properties"]["im_auth"] = auth_data

        if domain:
            tosca_comp["topology_template"]["inputs"]["domain_name"]["default"] = domain
        if app_name:
            tosca_comp["topology_template"]["inputs"]["app_name"]["default"] = app_name
        if influxdb_url:
            tosca_comp["topology_template"]["inputs"]["top_influx_url"]["default"] = influxdb_url
        if influxdb_token:
            tosca_comp["topology_template"]["inputs"]["top_influx_token"]["default"] = influxdb_token
        if qos_constraints:
            tosca_comp["topology_template"]["inputs"]["qos_constraints"]["default"] = qos_constraints

        tosca_comp["topology_template"]["inputs"]["layer_num"]["default"] = layer_num
        tosca_comp["topology_template"]["inputs"]["cluster_name"]["default"] = gen_oscar_name()
        tosca_comp["topology_template"]["inputs"]["admin_token"]["default"] = get_random_string(16)
        tosca_comp["topology_template"]["inputs"]["oscar_password"]["default"] = get_random_string(16)
        tosca_comp["topology_template"]["inputs"]["minio_password"]["default"] = get_random_string(16)
        tosca_comp["topology_template"]["inputs"]["local_influx_token"]["default"] = get_random_string(16)
        tosca_comp["topology_template"]["inputs"]["local_influx_pass"]["default"] = get_random_string(16)
        tosca_comp["topology_template"]["inputs"]["fe_os_image"]["default"] = None

        # Add SSH info for the Front-End node
        if compute_layer["type"] == "PhysicalToBeProvisioned":
            if not phys_nodes:
                raise Exception("Computational layer of type PhysicalToBeProvisioned, "
                                "but Physical Data File not exists.")
            # Add nets to enable to set IP of the nodes
            tosca_comp = add_nets(tosca_comp)
            pub_ip = get_physical_resource_data(compute_layer, res, phys_nodes, "fe_node", "public_ip")
            priv_ip = get_physical_resource_data(compute_layer, res, phys_nodes, "fe_node", "private_ip")
            tosca_comp = set_ip_details(tosca_comp, "front", "pub_network", pub_ip, 1)
            tosca_comp = set_ip_details(tosca_comp, "front", "priv_network", priv_ip, 0)
            ssh_user = get_physical_resource_data(compute_layer, res, phys_nodes, "fe_node", "ssh_user")
            ssh_key = get_physical_resource_data(compute_layer, res, phys_nodes, "fe_node", "ssh_key")
            set_node_credentials(tosca_comp["topology_template"]["node_templates"]["front"], ssh_user, ssh_key)

        for res_id, res in compute_layer["Resources"].items():
            if res["name"] != res_name:
                continue
            tosca_wn = copy.deepcopy(wn_tosca_tpl)
            wn_name = res_id

            wn_node = tosca_wn["topology_template"]["node_templates"].pop("wn_node")
            wn_node["requirements"][0]["host"] = "wn_%s" % wn_name

            wn = tosca_wn["topology_template"]["node_templates"].pop("wn")
            wn["capabilities"]["scalable"]["properties"]["count"] = res.get("totalNodes")
            if res.get("flavorName"):
                wn["capabilities"]["host"]["properties"]["instance_type"] = res.get("flavorName")
            wn["capabilities"]["host"]["properties"]["mem_size"] = "%s MB" % res.get("memorySize")
            wn["capabilities"]["host"]["properties"]["preemtible_instance"] = res.get("onSpot", False)

            wn["capabilities"]["os"]["properties"]["distribution"] = res.get("operatingSystemDistribution")
            wn["capabilities"]["os"]["properties"]["version"] = res.get("operatingSystemVersion")
            wn["capabilities"]["os"]["properties"]["image"] = res.get("operatingSystemImageId")

            # For the FE set the image of the first WN
            if tosca_comp["topology_template"]["inputs"]["fe_os_image"]["default"] is None:
                tosca_comp["topology_template"]["inputs"]["fe_os_image"]["default"] = res.get("operatingSystemImageId")

            cores = 0
            sgx = False
            for proc in list(res["processors"].values()):
                cores += proc.get("computingUnits", 0)
                if proc.get("SGXFlag"):
                    sgx = True

            gpus = 0
            gpu_arch = None
            for acc in list(res.get("accelerators", {}).values()):
                for proc in list(acc["processors"].values()):
                    if proc.get("type") == "GPU":
                        gpus += proc.get("computingUnits", 0)
                        gpu_arch = proc.get("architecture")

            wn["capabilities"]["host"]["properties"]["num_cpus"] = cores
            wn["capabilities"]["host"]["properties"]["sgx"] = sgx
            if gpus:
                wn["capabilities"]["host"]["properties"]["num_gpus"] = gpus
                if gpu_arch:
                    # We asume this format: gpu_model = vendor model
                    gpu_arch_parts = gpu_arch.split()
                    if len(gpu_arch_parts) != 2:
                        raise Exception("GPU architecture must be with format: VENDOR MODEL")
                    wn["capabilities"]["host"]["properties"]["gpu_vendor"] = gpu_arch_parts[0]
                    wn["capabilities"]["host"]["properties"]["gpu_model"] = gpu_arch_parts[1]

            if compute_layer["type"] == "PhysicalToBeProvisioned":
                # as each wn will have different ip, we have to create
                # one node per wn to reach totalNodes
                wn["capabilities"]["scalable"]["properties"]["count"] = 1
                if not phys_nodes:
                    raise Exception("Computational layer of type PhysicalToBeProvisioned,"
                                    " but Physical Data File not exists.")
                for num in range(0, res.get("totalNodes")):
                    ssh_user = get_physical_resource_data(compute_layer, res, phys_nodes, "wns", "ssh_user", num)
                    ssh_key = get_physical_resource_data(compute_layer, res, phys_nodes, "wns", "ssh_key", num)
                    set_node_credentials(wn, ssh_user, ssh_key)

                    wn_ip = get_physical_resource_data(compute_layer, res, phys_nodes, "wns", "private_ip", num)
                    tosca_comp = set_ip_details(tosca_comp, "wn_%s_%s" % (wn_name, num+1), "priv_network", wn_ip, 0)
                    tosca_wn["topology_template"]["node_templates"]["wn_node_%s_%s" % (wn_name, num+1)] = \
                        copy.deepcopy(wn_node)
                    tosca_wn["topology_template"]["node_templates"]["wn_%s_%s" % (wn_name, num+1)] = \
                        copy.deepcopy(wn)
                    tosca_res = merge_templates(tosca_comp, tosca_wn)
            elif compute_layer["type"] == "Virtual":
                tosca_wn["topology_template"]["node_templates"]["wn_node_%s" % wn_name] = wn_node
                tosca_wn["topology_template"]["node_templates"]["wn_%s" % wn_name] = wn
                tosca_res = merge_templates(tosca_comp, tosca_wn)
                if elastic:
                    if len(compute_layer["Resources"]) > 1:
                        raise Exception("Elastic option cannot be using with heterogeneous WNs.")
                    ec_fe["requirements"][1]["wn"] = "wn_node_%s" % wn_name

    elif compute_layer["type"] == "PhysicalAlreadyProvisioned":
        if len(compute_layer["Resources"]) != 1:
            raise Exception("PhysicalAlreadyProvisioned ComputeLayer must only have 1 resource.")
        if not phys_nodes:
            raise Exception("Computational layer of type PhysicalToBeProvisioned,"
                            " but Physical Data File not exists.")
        res = list(compute_layer["Resources"].values())[0]
        influx_endpoint = get_physical_resource_data(compute_layer, res, phys_nodes, "influx", "endpoint")
        influx_token = get_physical_resource_data(compute_layer, res, phys_nodes, "influx", "token")
        minio_endpoint = get_physical_resource_data(compute_layer, res, phys_nodes, "minio", "endpoint")
        minio_ak = get_physical_resource_data(compute_layer, res, phys_nodes, "minio", "access_key")
        minio_sk = get_physical_resource_data(compute_layer, res, phys_nodes, "minio", "secret_key")
        oscar_name = get_physical_resource_data(compute_layer, res, phys_nodes, "oscar", "name")

        tosca_res["topology_template"]["inputs"]["minio_endpoint"] = {"default": minio_endpoint, "type": "string"}
        tosca_res["topology_template"]["inputs"]["influx_endpoint"] = {"default": influx_endpoint, "type": "string"}
        tosca_res["topology_template"]["inputs"]["influx_token"] = {"default": influx_token, "type": "string"}
        tosca_res["topology_template"]["inputs"]["minio_ak"] = {"default": minio_ak, "type": "string"}
        tosca_res["topology_template"]["inputs"]["minio_sk"] = {"default": minio_sk, "type": "string"}
        tosca_res["topology_template"]["inputs"]["oscar_name"] = {"default": oscar_name, "type": "string"}
    elif compute_layer["type"] == "NativeCloudFunction":
        tosca_res["topology_template"]["inputs"]["aws"] = {"default": True, "type": "boolean"}
        tosca_res["topology_template"]["inputs"]["top_influx_url"] = {"default": influxdb_url, "type": "string"}
        tosca_res["topology_template"]["inputs"]["top_influx_token"] = {"default": influxdb_token, "type": "string"}

        if not phys_nodes:
            raise Exception("Computational layer of type NativeCloudFunction,"
                            " but Physical Data File not exists.")
        res = list(compute_layer["Resources"].values())[0]
        aws_region = get_physical_resource_data(compute_layer, res, phys_nodes, "aws", "region")
        aws_bucket = get_physical_resource_data(compute_layer, res, phys_nodes, "aws", "bucket")
        aws_ak = get_physical_resource_data(compute_layer, res, phys_nodes, "aws", "access_key")
        aws_sk = get_physical_resource_data(compute_layer, res, phys_nodes, "aws", "secret_key")

        tosca_res["topology_template"]["inputs"]["aws_region"] = {"default": aws_region, "type": "string"}
        tosca_res["topology_template"]["inputs"]["aws_bucket"] = {"default": aws_bucket, "type": "string"}
        tosca_res["topology_template"]["inputs"]["aws_ak"] = {"default": aws_ak, "type": "string"}
        tosca_res["topology_template"]["inputs"]["aws_sk"] = {"default": aws_sk, "type": "string"}

    return tosca_res
