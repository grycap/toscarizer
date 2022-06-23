import yaml
import copy

from oscariser.utils import RESOURCES_FILE

TOSCA_TEMPLATE = "templates/oscar.yaml"


def gen_oscar_name():
    # TODO: https://github.com/grycap/im-dashboard/blob/master/app/utils.py#L435
    return None


def gen_tosca_yaml(resource_file):
    with open(TOSCA_TEMPLATE, 'r') as f:
        tosca_tpl = yaml.safe_load(f)

    inputs = gen_tosca_input_value(resource_file)
    res = {}
    for cl, input_values in inputs.items():
        res[cl] = copy.deepcopy(tosca_tpl)
        for input_name, input_value in input_values.items():
            if input_value is not None and input_name in res[cl]["topology_template"]["inputs"]:
                res[cl]["topology_template"]["inputs"][input_name] = input_value

    return res


def gen_tosca_input_value(resource_file):
    """Parse the resources.yaml file."""
    input_values = {}
    try:
        with open(resource_file, 'r') as f:
            resources = yaml.safe_load(f)

        for nd in list(resources["System"]["NetworkDomains"].values()):
            for cl_name, cl in nd["ComputationalLayers"].items():
                if cl["type"] == "Virtual":
                    input_values[cl_name] = {}
                    for res in list(cl["Resources"].values()):
                        input_values[cl_name]["cluster_name"] = gen_oscar_name()
                        input_values[cl_name]["wn_num"] = res.get("totalNodes")
                        input_values[cl_name]["os_type"] = res.get("operatingSystemType")
                        input_values[cl_name]["os_distribution"] = res.get("operatingSystemDistribution")
                        input_values[cl_name]["os_version"] = res.get("operatingSystemVersion")
                        input_values[cl_name]["os_image"] = res.get("operatingSystemImageId")
                        if res.get("memorySize"):
                            input_values[cl_name]["wn_mem"] = "%s MB" % res.get("memorySize")
                        if res.get("storageSize"):
                            input_values[cl_name]["storage_size"] = "%s GB" % res.get("storageSize")
                        if res.get("storageType") == "SSD":
                            # TODO: Improve
                            input_values[cl_name]["volume_type"] = "gp3"
                        input_values[cl_name]["wn_preemtible_instance"] = res.get("onSpot")

                        cores = 0
                        sgx = None
                        for proc in list(res["processors"].values()):
                            cores += proc.get("computingUnits", 0)
                            sgx = proc.get("SGXFlag")

                        input_values[cl_name]["wn_cpus"] = cores
                        input_values[cl_name]["wn_sgx"] = sgx

                        for acc in list(res.get("accelerators", {}).values()):
                            # TODO: look for GPUs
                            pass

    except Exception as ex:
        print("Error reading resources.yaml: %s" % ex)
    return input_values


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        dir = sys.argv[1]
    else:
        dir = "."

    for cl, tosca in gen_tosca_yaml("%s/%s" % (dir, RESOURCES_FILE)).items():
        print("TOSCA for Computational Layer: %s" % cl)
        print(yaml.safe_dump(tosca, indent=2))
