from toscarizer.utils import RESOURCES_COMPLETE_FILE, BASE_DAG_FILE, parse_dag, parse_resources


def get_image_url(component, resources, containers):
    arch = "amd64"
    if "arm64" in resources[component]["platforms"]:
        arch = "arm64"
    for images in list(containers["components"].values()):
        for image in images["docker_images"]:
            if "/%s_%s" % (component, arch) in image or "/%s_base_%s" % (component, arch) in image:
                return image
    return None


def get_service(component, previous, resources, containers):
    """Generate the OSCAR service FDL."""
    if not previous:
        input_path = "%s/input" % component
    else:
        input_path = "%s/output" % previous
    service = {
        "name": component,
        "image": get_image_url(component, resources, containers),
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


def generate_fdl(dag, resources, containers):
    """Generates the FDL for the dag and resources provided."""
    fdl = {"functions": {"oscar": []}}
    oscar = fdl["functions"]["oscar"]
    components_done = []

    for component, next_items in dag.adj.items():
        # Using the name of the computationallayer
        # asuming that it is computationallayer + the num
        cluster_name = resources.get(component, {}).get("layers", [{"name": "computationallayer0"}])[0]["name"]
        # Add the node
        if component not in components_done:
            service = get_service(component, None, resources, containers)
            oscar.append({cluster_name: service})
            components_done.append(component)

        # Add the neighbours of this node
        for next_component in next_items:
            cluster_name = "computationallayer%s" % resources.get(next_component, {}).get("layer", "0")
            if next_component not in components_done:
                service = get_service(next_component, component, resources, containers)
                oscar.append({cluster_name: service})
                components_done.append(next_component)

    return fdl