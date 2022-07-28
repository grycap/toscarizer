import yaml
import copy
import random
import string

from toscarizer.utils import RESOURCES_FILE

TOSCA_TEMPLATE = "templates/oscar.yaml"
WN_TOSCA_TEMPLATE = "templates/oscar_wn.yaml"

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
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


def find_compute_layer(resources, layer_num):
    for nd in list(resources["System"]["NetworkDomains"].values()):
        if "ComputationalLayers" in nd:
            for _, cl in nd["ComputationalLayers"].items():
                if cl.get("number") == layer_num:
                    return cl
    return None


def find_resource_by_name(compute_layer, res_name):
    for res in list(compute_layer["Resources"].values()):
        if res.get("name") == res_name:
            return res
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


def gen_tosca_yamls(resource_file):
    with open(TOSCA_TEMPLATE, 'r') as f:
        tosca_tpl = yaml.safe_load(f)

    with open(WN_TOSCA_TEMPLATE, 'r') as f:
        wn_tosca_tpl = yaml.safe_load(f)

    tosca_res = {}
    try:
        with open(resource_file, 'r') as f:
            resources = yaml.safe_load(f)

        for comp_id, component in resources["System"]["Components"].items():
            tosca_comp = copy.deepcopy(tosca_tpl)
            compute_layer = find_compute_layer(resources, component["executionLayer"])
            if not compute_layer:
                raise Exception("No compute layer %s found." % component["executionLayer"])

            if compute_layer["type"] == "PhysicalAlreadyProvisioned":
                # Add nets to enable to set IP of the nodes
                tosca_comp = add_nets(tosca_comp)
                tosca_comp = set_ip_details(tosca_comp, "front", "pub_network", "TODO-pub", 1)
                tosca_comp = set_ip_details(tosca_comp, "front", "priv_network", "TODO-priv", 0)
                set_node_credentials(tosca_comp["topology_template"]["node_templates"]["front"], "TODO", "TODO")

            if compute_layer["type"] != "NativeCloudFunction":
                tosca_comp["topology_template"]["inputs"]["cluster_name"]["default"] = gen_oscar_name()
                tosca_comp["topology_template"]["inputs"]["domain_name"]["default"] = "im.grycap.net"
                tosca_comp["topology_template"]["inputs"]["admin_token"]["default"] = get_random_string(16)
                tosca_comp["topology_template"]["inputs"]["oscar_password"]["default"] = get_random_string(16)
                tosca_comp["topology_template"]["inputs"]["minio_password"]["default"] = get_random_string(16)
                tosca_comp["topology_template"]["inputs"]["fe_os_image"]["default"] = None
                for cont_id, cont in component["Containers"].items():
                    res = find_resource_by_name(compute_layer, cont["selectedExecutionResource"])
                    if not res:
                        raise Exception("Not resource %s in compute layer %s." % (cont["selectedExecutionResource"],
                                                                                    component["executionLayer"]))
                    tosca_wn = copy.deepcopy(wn_tosca_tpl)
                    wn_name = "%s_%s" % (component["name"], cont_id)

                    wn_node = tosca_wn["topology_template"]["node_templates"].pop("wn_node")
                    wn_node["requirements"][0]["host"] = "wn_%s" % wn_name

                    wn = tosca_wn["topology_template"]["node_templates"].pop("wn")
                    wn["capabilities"]["scalable"]["properties"]["count"] = res.get("totalNodes")
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

                    for acc in list(res.get("accelerators", {}).values()):
                        # TODO: look for GPUs
                        pass

                    wn["capabilities"]["host"]["properties"]["num_cpus"] = cores
                    wn["capabilities"]["host"]["properties"]["sgx"] = sgx

                    if compute_layer["type"] == "PhysicalAlreadyProvisioned":
                        set_node_credentials(wn, "TODO", "TODO")
                        # as each wn will have different ip, we have to create 
                        # one node per wn to reach totalNodes
                        wn["capabilities"]["scalable"]["properties"]["count"] = 1
                        for num in range(1, res.get("totalNodes")):
                            # TODO: Get the WN ip
                            wn_ip = "TODO-priv-%s" % num
                            tosca_comp = set_ip_details(tosca_comp, "wn_%s_%s" % (wn_name, num), "priv_network", wn_ip, 0)
                            tosca_wn["topology_template"]["node_templates"]["wn_node_%s_%s" % (wn_name, num)] = copy.deepcopy(wn_node)
                            tosca_wn["topology_template"]["node_templates"]["wn_%s_%s" % (wn_name, num)] = copy.deepcopy(wn)
                            tosca_res[component["name"]] = merge_templates(tosca_comp, tosca_wn)
                    else:
                        tosca_wn["topology_template"]["node_templates"]["wn_node_%s" % wn_name] = wn_node
                        tosca_wn["topology_template"]["node_templates"]["wn_%s" % wn_name] = wn

                        tosca_res[component["name"]] = merge_templates(tosca_comp, tosca_wn)

    except Exception as ex:
        print("Error reading resources file: %s" % ex)

    return tosca_res
