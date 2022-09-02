import docker
import yaml
import os
import shutil


from toscarizer.utils import ANNOTATIONS_FILE, CONTAINERS_FILE, RESOURCES_FILE, COMPONENT_FILE, parse_resources


DOCKERFILE_TEMPLATE = "templates/Dockerfile.template"
SCRIPT_TEMPLATE = "templates/script.sh"


def get_part_x_name(part_name):
    """Replaces first num of partition with an X"""
    ini = part_name.find("_partition")
    end = part_name.find("_", ini + 10)
    return part_name[:ini + 10] + "X" + part_name[end:]


def generate_dockerfiles(app_dir, components, resources):
    """Generates dockerfiles per each component using the template."""
    with open(DOCKERFILE_TEMPLATE, 'r') as f:
        dockerfile_tpl = f.read()

    dockerfiles = {}
    for component, partitions in components["components"].items():
        dockerfiles[component] = {}
        for partition in partitions["partitions"]:
            dockerfiles[component][partition] = []
            dockerfile_path = "%s/aisprint/designs/%s/%s/Dockerfile" % (app_dir, component, partition)
            dockerfile = dockerfile_tpl.replace("{{component_name}}", "%s_%s" % (component, partition))
            with open(dockerfile_path, 'w+') as f:
                f.write(dockerfile)
            if partition == "base":
                part_name = component
            else:
                part_name = "%s_%s" % (component, partition)

            if part_name not in resources:
                part_name = get_part_x_name(part_name)

            for platform in resources[part_name]["platforms"]:
                dockerfiles[component][partition].append(("linux/%s" % platform, dockerfile_path))

    return dockerfiles


def build_and_push(registry, registry_folder, dockerfiles, username, password, push=True, build=True):
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
                    name = "%s_%s_amd64" % (component, partition)
                else:
                    name = "%s_%s_arm64" % (component, partition)
                if registry_folder.startswith("/"):
                    registry_folder = registry_folder[1:]
                image = "%s/%s/%s:latest" % (registry, registry_folder, name)
                if build:
                    build_dir = os.path.dirname(dockerfile)
                    # Copy the script that is generic
                    shutil.copy(SCRIPT_TEMPLATE, build_dir)
                    dclient.images.build(path=build_dir, tag=image, pull=True, platform=platform)

                # Pushing new image
                res[component][partition].append(image)
                if push:
                    for line in dclient.images.push(image, stream=True, decode=True):
                        if 'error' in line:
                            raise Exception("Error pushing image: %s" % line['errorDetail']['message'])
            os.unlink(dockerfile)

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
