import sys
import yaml
from oscariser.utils import RESOURCES_FILE, DAG_FILE, parse_dag, parse_resources


def get_service(component, previous, resources):
    """Generate the OSCAR service FDL."""
    if not previous:
        input_path = "%s/input" % component
    else:
        input_path = "%s/output" % previous
    if not resources.get(component, {}).get("containerLink"):
        raise Exception("No containerLink found for component: %s" % component)
    service = {
        "name": component,
        "image": resources.get(component, {}).get("containerLink"),
        "script": "%s_script.sh" % component,
        "input": [{
            "storage_provider": "minio",
            "path": input_path
        }],
        "output": [{
            "storage_provider": "minio",
            "path": "%s/output" % component
        }],
        "memory": "%sMi" % resources.get(component, {}).get("memory", 512),
        "cpu": resources.get(component, {}).get("cpu", "1")
    }
    return service


def generate_fdl(dag, resources):
    """Generates the FDL for the dag and resources provided."""
    fdl = {"functions": {"oscar": []}}
    oscar = fdl["functions"]["oscar"]
    components_done = []

    for component, next_items in dag.adj.items():
        # Using the name of the computationallayer
        # asuming that it is computationallayer + the num
        cluster_name = "computationallayer%s" % resources.get(component, {}).get("layer", "0")
        # Add the node
        if component not in components_done:
            service = get_service(component, None, resources)
            oscar.append({cluster_name: service})
            components_done.append(component)

        # Add the neighbours of this node
        for next_component in next_items:
            cluster_name = "computationallayer%s" % resources.get(next_component, {}).get("layer", "0")
            if next_component not in components_done:
                service = get_service(next_component, component, resources)
                oscar.append({cluster_name: service})
                components_done.append(next_component)

    return fdl


if __name__ == "__main__":
    if len(sys.argv) > 1:
        dir = sys.argv[1]
    else:
        dir = "."

    resources = parse_resources("%s/%s" % (dir, RESOURCES_FILE))
    dag = parse_dag("%s/%s" % (dir, DAG_FILE))

    fdl = generate_fdl(dag, resources)

    print(yaml.safe_dump(fdl, indent=2))
