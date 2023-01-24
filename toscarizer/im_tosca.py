import yaml
import copy
import random
import string
import os.path


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
    for nd in list(resources["System"]["NetworkDomains"].values()):
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
                    return res_name, cont, cl_name
    return None


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


def gen_tosca_yamls(dag, resources_file, deployments_file, phys_file, elastic, auth_data):
    with open(deployments_file, 'r') as f:
        deployments = yaml.safe_load(f)
        if "System" in deployments:
            deployments = deployments["System"]
    with open(resources_file, 'r') as f:
        full_resouces = yaml.safe_load(f)

    phys_nodes = {}
    if phys_file:
        with open(phys_file, 'r') as f:
            phys_nodes = yaml.safe_load(f)

    # Get a dict of ComputationalLayers by name
    cls = {}
    for nd in list(full_resouces["System"]["NetworkDomains"].values()):
        if "ComputationalLayers" in nd:
            for cl_name, cl in nd["ComputationalLayers"].items():
                cls[cl_name] = cl

    # Create the OSCAR clusters per component
    oscar_clusters_per_component = {}
    container_per_component = {}
    for component in dag.nodes():
        # First find the Component cluster
        res_name, cont, cl_name = find_compute_layer(full_resouces, component, deployments["Components"])
        container_per_component[component] = cont
        if not cl_name:
            raise Exception("No compute layer found for component." % component.get("name"))
        oscar_clusters_per_component[component] = gen_tosca_cluster(cls[cl_name], res_name, phys_nodes, elastic, auth_data)

    # Now create the OSCAR services and merge in the correct OSCAR cluster
    for component, next_items in dag.adj.items():
        # Add the node
        oscar_service = get_service(component, next_items, list(dag.predecessors(component)),
                                    container_per_component[component], oscar_clusters_per_component)
        oscar_clusters_per_component[component] = merge_templates(oscar_clusters_per_component[component],
                                                                  oscar_service)

    return oscar_clusters_per_component


def get_service(component, next_items, prev_items, container, oscar_clusters):
    """Generate the OSCAR service TOSCA."""
    service = {
        "type": "tosca.nodes.aisprint.FaaS.Function",
        "properties": {
            "name": component.replace("_", "-"),
            "image": container.get("image"),
            "script": "/opt/%s/script.sh" % component,
            "input": [{
                "storage_provider": "minio",
                "path": "%s/input" % component.replace("_", "-")
            }],
            "output": [
                {
                    "storage_provider": "minio",
                    "path": "%s/output" % component.replace("_", "-")
                }
            ],
            "memory": "%sMi" % container.get("memorySize", 512),
            "cpu": container.get("computingUnits", "1"),
            "env_variables": {
                "COMPONENT_NAME": component,
                "MONIT_HOST": "ai-sprint-%s-app-telegraf" % component,
                "MONIT_PORT": "8094"
            }
        }
    }

    cluster_inputs = oscar_clusters[component]["topology_template"]["inputs"]
    if len(oscar_clusters[component]["topology_template"]["node_templates"]) > 1:
        # It is a IM deployed cluster
        # Use the minio url as we alredy have it
        service["properties"]["env_variables"]["KCI"] = \
            "https://minio.%s.%s" % (cluster_inputs["cluster_name"]["default"],
                                     cluster_inputs["domain_name"]["default"])
    else:
        # It is an already existing OSCAR cluster
        service["properties"]["env_variables"]["KCI"] = cluster_inputs["minio_endpoint"]["default"]

    storage_providers = {}

    # Add inputs (All must be in the local cluster)
    for prev_item in prev_items:
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
                service["properties"]["output"].append({
                    "storage_provider": "minio.%s" % cluster_name,
                    "path": "%s/output" % component.replace("_", "-")
                })

    if len(oscar_clusters[component]["topology_template"]["node_templates"]) > 1:
        service["requirements"] = [
            {"host": "oscar"}
        ]

    if storage_providers:
        service["properties"]["storage_providers"] = {"minio": storage_providers}

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


def gen_tosca_cluster(compute_layer, res_name, phys_nodes, elastic, auth_data):
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
            "node_templates": {}
        }
    }

    if compute_layer["type"] in ["Virtual", "PhysicalToBeProvisioned"]:
        tosca_comp = copy.deepcopy(tosca_tpl)
        if elastic:
            tosca_comp["topology_template"]["node_templates"].update(elastic_tosca_tpl)
            tosca_comp["topology_template"]["inputs"]["max_wn_num"]["default"] = elastic
            ec_fe = tosca_comp["topology_template"]["node_templates"]["elastic_cluster_front_end"]
            ec_fe["properties"]["im_auth"] = auth_data

        tosca_comp["topology_template"]["inputs"]["cluster_name"]["default"] = gen_oscar_name()
        tosca_comp["topology_template"]["inputs"]["admin_token"]["default"] = get_random_string(16)
        tosca_comp["topology_template"]["inputs"]["oscar_password"]["default"] = get_random_string(16)
        tosca_comp["topology_template"]["inputs"]["minio_password"]["default"] = get_random_string(16)
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
        tosca_res["topology_template"]["inputs"] = {}

        if len(compute_layer["Resources"]) != 1:
            raise Exception("PhysicalAlreadyProvisioned ComputeLayer must only have 1 resource.")
        res = list(compute_layer["Resources"].values())[0]
        minio_endpoint = get_physical_resource_data(compute_layer, res, phys_nodes, "minio", "endpoint")
        minio_ak = get_physical_resource_data(compute_layer, res, phys_nodes, "minio", "access_key")
        minio_sk = get_physical_resource_data(compute_layer, res, phys_nodes, "minio", "secret_key")
        oscar_name = get_physical_resource_data(compute_layer, res, phys_nodes, "oscar", "name")

        tosca_res["topology_template"]["inputs"]["minio_endpoint"] = {"default": minio_endpoint, "type": "string"}
        tosca_res["topology_template"]["inputs"]["minio_ak"] = {"default": minio_ak, "type": "string"}
        tosca_res["topology_template"]["inputs"]["minio_sk"] = {"default": minio_sk, "type": "string"}
        tosca_res["topology_template"]["inputs"]["oscar_name"] = {"default": oscar_name, "type": "string"}
    return tosca_res
