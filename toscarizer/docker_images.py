import docker
import tempfile
import yaml
from toscarizer.utils import RESOURCES_FILE, DAG_FILE, parse_dag, parse_resources


DOCKERFILE_TEMPLATE = "templates/Dockerfile.template"


def generate_dockerfiles(dag, resources):
    """Generates dockerfiles per each component using the template."""
    with open(DOCKERFILE_TEMPLATE, 'r') as f:
        dockerfile_tpl = f.read()

    dockerfiles = {}
    for component in dag:
        dockerfiles[component] = (resources[component]["image"],
                                  dockerfile_tpl.replace("{{component_name}}", component))

    return dockerfiles


def build_and_push(registry, dockerfiles, username, password, platform=None, push=True, build=True):
    """Build and push the images per each component using the dockerfiles specified."""
    try:
        dclient = docker.from_env()
    except docker.errors.DockerException:
        raise Exception("Error getting docker client. Check if current user"
                        " has the correct permissions (docker group).")

    if push:
        dclient.login(username=username, password=password, registry=registry)

    res = {}
    for name, elem in dockerfiles.items():
        image_name, dockerfile = elem
        image = "%s/%s:latest" % (registry, image_name)
        with tempfile.TemporaryDirectory() as tmpdirname:
            with open("%s/Dockerfile" % tmpdirname, 'w') as f:
                f.write(dockerfile)
                if build:
                    dclient.images.build(path=tmpdirname, tag=image, pull=True, platform=platform)

        # Pushing new image
        res[name] = (True, image)
        if push:
            for line in dclient.images.push(image, stream=True, decode=True):
                if 'error' in line:
                    res[name] = (False, "Error pushing image: %s" % line['errorDetail']['message'])

    return res


def update_resources(docker_images, resource_file):
    """Update the resources.yaml file adding the containerLink."""
    with open(resource_file, 'r') as f:
        resources = yaml.safe_load(f)

    for _, elem in resources["System"]["Components"].items():
        success, image_name = docker_images.get(elem["name"], (False, None))
        if success:
            cont_name = list(elem["Containers"].keys())[0]
            elem["Containers"][cont_name]["containerLink"] = image_name

    with open(resource_file, 'w') as f:
        f.write(yaml.safe_dump(resources, indent=2))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        dir = sys.argv[1]
    else:
        dir = "."

    resources = parse_resources("%s/%s" % (dir, RESOURCES_FILE))
    dag = parse_dag("%s/%s" % (dir, DAG_FILE))

    dockerfiles = generate_dockerfiles(dag, resources)

    registry = "registry.gitlab.polimi.it/ai-sprint"
    username = ""
    password = ""

    docker_images = build_and_push(registry, dockerfiles, username, password, None, False, False)

    update_resources(docker_images, "%s/%s" % (dir, RESOURCES_FILE))
