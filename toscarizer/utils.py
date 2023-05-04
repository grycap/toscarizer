import networkx as nx
import yaml

# Default file names
RESOURCES_FILE = "common_config/candidate_resources.yaml"
DEPLOYMENTS_FILE = "common_config/candidate_deployments.yaml"
COMPONENT_FILE = "aisprint/designs/component_partitions.yaml"
CONTAINERS_FILE = "aisprint/designs/containers.yaml"
ANNOTATIONS_FILE = "common_config/annotations.yaml"
PHYSICAL_NODES_FILE = "common_config/physical_nodes.yaml"

BASE_RESOURCES_COMPLETE_FILE = "aisprint/deployments/base/production_deployment.yaml"
RESOURCES_COMPLETE_FILE = "aisprint/deployments/optimal_deployment/production_deployment.yaml"
BASE_DAG_FILE = "aisprint/deployments/base/application_dag.yaml"
OPTIMAL_DAG_FILE = "aisprint/deployments/optimal_deployment/application_dag.yaml"

QOS_CONSTRAINTS_FILE = "aisprint/deployments/base/ams/qos_constraints.yaml"
OPTIMAL_QOS_CONSTRAINTS_FILE = "aisprint/deployments/optimal_deployment/ams/qos_constraints.yaml"


def parse_dag(dag_file):
    """Pase the application_dag.yml fila and return a networkx.DiGraph."""
    with open(dag_file, 'r') as f:
        dag = yaml.safe_load(f)

    dag = dag['System']

    G = nx.DiGraph()
    for source, target, weight in dag['dependencies']:
        G.add_edge(source, target, weight=weight)

    return dag["name"], G


def parse_resources(resource_file, deployments_files):
    """Parse the resources.yaml file."""
    res_dict = {}
    try:
        with open(resource_file, 'r') as f:
            resources = yaml.safe_load(f)
        with open(deployments_files, 'r') as f:
            deployments = yaml.safe_load(f)

        cls = {}
        for _, nd in resources["System"]["NetworkDomains"].items():
            if "ComputationalLayers" in nd:
                for cl_name, cl in nd["ComputationalLayers"].items():
                    cls[cl["number"]] = {"name": cl_name, "resources": {}}
                    if cl["type"] == "NativeCloudFunction":
                        cls[cl["number"]]["aws"] = True
                    for res in list(cl["Resources"].values()):
                        cls[cl["number"]]["resources"][res["name"]] = {}
                        if res.get("architecture"):
                            cls[cl["number"]]["resources"][res["name"]]["arch"] = res.get("architecture")
                        else:
                            for proc in (res.get("processors", {}).values()):
                                cls[cl["number"]]["resources"][res["name"]]["arch"] = proc["architecture"]

                        if cls[cl["number"]]["resources"][res["name"]]["arch"] not in ["arm64", "amd64"]:
                            raise Exception("Invalid architecture specified. Valid values: arm64 or amd64.")

        if "System" in deployments:
            deployments = deployments["System"]

        for cname, elem in deployments["Components"].items():
            layers = {}
            if "candidateExecutionLayers" in elem:
                layers = [cls[layer_num] for layer_num in elem["candidateExecutionLayers"]]
            elif "executionLayer" in elem:
                layers = [cls[elem["executionLayer"]]]
            else:
                raise Exception("Error: no candidateExecutionLayers nor "
                                "executionLayer defined in Component: %s" % cname)

            platforms = []
            aws = False
            for layer in layers:
                if "aws" in layer and layer["aws"]:
                    aws = True
                for r in list(layer["resources"].values()):
                    if r["arch"] not in platforms:
                        platforms.append(r["arch"])

            res_dict[elem["name"]] = {"platforms": platforms,
                                      "aws": aws,
                                      "layers": layers}
    except Exception as ex:
        print("Error reading resources.yaml: %s" % ex)
    return res_dict
