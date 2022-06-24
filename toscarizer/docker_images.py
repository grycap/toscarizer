import docker
import tempfile
import yaml

from toscarizer.utils import CONTAINERS_FILE, RESOURCES_FILE, COMPONENT_FILE, parse_resources


DOCKERFILE_TEMPLATE = "templates/Dockerfile.template"


def generate_dockerfiles(components, resources):
    """Generates dockerfiles per each component using the template."""
    with open(DOCKERFILE_TEMPLATE, 'r') as f:
        dockerfile_tpl = f.read()

    dockerfiles = {}
    for component, partitions in components["components"].items():
        dockerfiles[component] = {}
        for partition in partitions["partitions"]:
            dockerfiles[component][partition] = []
            dockerfile = dockerfile_tpl.replace("{{component_name}}", partition)
            if resources[partition]["arm64"]:
                dockerfiles[component][partition].append(("linux/amd64", dockerfile))
                dockerfiles[component][partition].append(("linux/arm64", dockerfile))
            else:
                dockerfiles[component][partition].append(("linux/amd64", dockerfile))

    return dockerfiles


def build_and_push(registry, dockerfiles, username, password, push=True, build=True):
    """Build and push the images per each component using the dockerfiles specified."""
    try:
        dclient = docker.from_env()
    except docker.errors.DockerException:
        raise Exception("Error getting docker client. Check if current user"
                        " has the correct permissions (docker group).")

    if push:
        dclient.login(username=username, password=password, registry=registry)

    res = {}
    for component, partitions in dockerfiles.items():
        res[component] = {}
        for partition, docker_images in partitions.items():
            res[component][partition] = []
            for (platform, dockerfile) in docker_images:
                if platform == "linux/amd64":
                    name = "%s_AMD64" % partition
                else:
                    name = "%s_ARM64" % partition
                image = "%s/%s:latest" % (registry, name)
                with tempfile.TemporaryDirectory() as tmpdirname:
                    with open("%s/Dockerfile" % tmpdirname, 'w') as f:
                        f.write(dockerfile)
                        if build:
                            dclient.images.build(path=tmpdirname, tag=image, pull=True, platform=platform)

                # Pushing new image
                res[component][partition].append(image)
                if push:
                    for line in dclient.images.push(image, stream=True, decode=True):
                        if 'error' in line:
                            raise Exception("Error pushing image: %s" % line['errorDetail']['message'])

    return res


def generate_containers(docker_images, containers_file):
    """Create the containers.yaml file adding the image URL."""
    containers = {"components": {}}

    for component, partitions in docker_images.items():
        containers["components"][component] = {"docker_images": []}
        for images in list(partitions.values()):
            for image_url in images:
                containers["components"][component]["docker_images"].append(image_url)

    with open(containers_file, 'w') as f:
        f.write(yaml.safe_dump(containers, indent=2))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        dir = sys.argv[1]
    else:
        dir = "/home/micafer/codigo/toscarizer/design_example/"

    resources = parse_resources("%s/%s" % (dir, RESOURCES_FILE))
    with open("%s/%s" % (dir, COMPONENT_FILE), 'r') as f:
        components = yaml.safe_load(f)

    dockerfiles = generate_dockerfiles(components, resources)

    registry = "registry.gitlab.polimi.it/ai-sprint"
    username = ""
    password = ""

    docker_images = build_and_push(registry, dockerfiles, username, password, False, False)

    generate_containers(docker_images, "%s/%s" % (dir, CONTAINERS_FILE))
