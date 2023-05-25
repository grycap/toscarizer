import docker
import yaml
import os
import shutil
from toscarizer.utils import read_env_vars


TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
DOCKERFILE_TEMPLATE = os.path.join(TEMPLATES_PATH, 'Dockerfile.template')
DOCKERFILE_AWS_TEMPLATE = os.path.join(TEMPLATES_PATH, 'Dockerfile.aws.template')
SCRIPT_TEMPLATE = os.path.join(TEMPLATES_PATH, 'script.sh')
START_TEMPLATE = os.path.join(TEMPLATES_PATH, 'start.sh')
TELEGRAF_TEMPLATE = os.path.join(TEMPLATES_PATH, 'telegraf.conf')


def get_part_x_name(part_name):
    """Replaces first num of partition with an X"""
    ini = part_name.find("_partition")
    end = part_name.find("_", ini + 10)
    return part_name[:ini + 10] + "X" + part_name[end:]


def generate_dockerfiles(base_image, app_dir, components, resources):
    """Generates dockerfiles per each component using the template."""
    with open(DOCKERFILE_TEMPLATE, 'r') as f:
        dockerfile_tpl = f.read()
    with open(DOCKERFILE_AWS_TEMPLATE, 'r') as f:
        dockerfile_aws_tpl = f.read()
    with open(SCRIPT_TEMPLATE, 'r') as f:
        scriptfile_tpl = f.read()

    dockerfiles = {}
    for component, partitions in components["components"].items():
        dockerfiles[component] = {}
        env_vars = read_env_vars(app_dir, component)
        for partition in partitions["partitions"]:
            if partition == "base":
                part_name = component
            else:
                part_name = "%s_%s" % (component, partition)

            if part_name not in resources:
                part_name = get_part_x_name(part_name)

            dockerfiles[component][partition] = []
            dockerfile_dir = "%s/aisprint/designs/%s/%s" % (app_dir, component, partition)
            dockerfile_path = "%s/Dockerfile" % dockerfile_dir
            dockerfile = "FROM %s\n%s\n%s" % (base_image,
                                              env_vars,
                                              dockerfile_tpl.replace("{{component_name}}", component))
            with open(dockerfile_path, 'w+') as f:
                f.write(dockerfile)

            # Generate image for SCAR in ECR
            if resources[part_name]["aws"]:
                dockerfile_path_aws = "%s/Dockerfile.aws" % dockerfile_dir
                dockerfile = "FROM %s\n%s\n%s\n%s" % (base_image,
                                                      env_vars,
                                                      dockerfile_tpl.replace("{{component_name}}", component),
                                                      dockerfile_aws_tpl)
                with open(dockerfile_path_aws, 'w+') as f:
                    f.write(dockerfile)
                shutil.copyfile(START_TEMPLATE, "%s/start.sh" % dockerfile_dir)
                shutil.copyfile(TELEGRAF_TEMPLATE, "%s/telegraf.conf" % dockerfile_dir)

            # Copy the script
            scriptfile = scriptfile_tpl.replace("{{component_name}}", component)
            scriptfile_path = "%s/script.sh" % dockerfile_dir
            with open(scriptfile_path, 'w+') as f:
                f.write(scriptfile)

            for platform in resources[part_name]["platforms"]:
                dockerfiles[component][partition].append(("linux/%s" % platform,
                                                          False,
                                                          dockerfile_path))
                if resources[part_name]["aws"]:
                    dockerfiles[component][partition].append(("linux/%s" % platform,
                                                              True,
                                                              dockerfile_path_aws))

    return dockerfiles


def build_and_push(registry, registry_folder, dockerfiles, ecr, push=True, build=True):
    """Build and push the images per each component using the dockerfiles specified."""
    try:
        dclient = docker.from_env()
    except docker.errors.DockerException:
        raise Exception("Error getting docker client. Check if current user"
                        " has the correct permissions (docker group).")

    res = {}
    for component, partitions in dockerfiles.items():
        res[component] = {}
        for partition, docker_images in partitions.items():
            res[component][partition] = []
            for (platform, aws, dockerfile) in docker_images:
                if platform == "linux/amd64":
                    name = "%s_%s_amd64" % (component, partition)
                else:
                    name = "%s_%s_arm64" % (component, partition)
                if registry_folder.startswith("/"):
                    registry_folder = registry_folder[1:]
                if aws:
                    if not ecr:
                        raise Exception("AWS ECR repository URL parameter not set.")
                    image = "%s:%s" % (ecr, name)
                else:
                    image = "%s/%s/%s:latest" % (registry, registry_folder, name)
                if build:
                    print("Building %simage: %s ..." % ("ECR " if aws else "", name))
                    dclient.images.build(path=os.path.dirname(dockerfile), tag=image, pull=True,
                                         platform=platform, dockerfile=os.path.basename(dockerfile))

                # Pushing new image
                res[component][partition].append(image)
                if push:
                    print("Pushing %simage: %s ..." % ("ECR " if aws else "", name))
                    for line in dclient.images.push(image, stream=True, decode=True):
                        if 'error' in line:
                            msg = line['errorDetail']['message']
                            if msg == 'EOF':
                                msg += ". Check if the ECR repo exists."
                            raise Exception("Error pushing image: %s" % msg)
            if build:
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
