import networkx as nx
import yaml

# Default file names
RESOURCES_FILE = "resources.yaml"
DAG_FILE = "application_dag.yaml"


def parse_dag(dag_file):
    """Pase the application_dag.yml fila and return a networkx.DiGraph."""
    with open(dag_file, 'r') as f:
        dag = yaml.safe_load(f)

    dag = dag['System']

    G = nx.DiGraph()
    for source, target, weight in dag['dependencies']:
        G.add_edge(source, target, weight=weight)

    return G


def parse_resources(resource_file):
    """Parse the resources.yaml file."""
    res_dict = {}
    try:
        with open(resource_file, 'r') as f:
            resources = yaml.safe_load(f)
        for _, elem in resources["System"]["Components"].items():
            # We assume that there will be only one container per component
            # and only one elem in the candidateExecutionLayers
            for _, cont in elem["Containers"].items():
                res_dict[elem["name"]] = {"memory": cont["memorySize"],
                                          "cpu": cont["computingUnits"],
                                          "layer": cont["candidateExecutionLayers"][0],
                                          "image": cont["image"],
                                          "containerLink": cont.get("containerLink")}
    except Exception as ex:
        print("Error reading resources.yaml: %s" % ex)
    return res_dict
