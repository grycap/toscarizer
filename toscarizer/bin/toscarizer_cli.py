import click
import yaml
import sys

sys.path.append(".")

from toscarizer.utils import parse_dag, parse_resources, RESOURCES_FILE, COMPONENT_FILE, CONTAINERS_FILE, DAG_FILE, RESOURCES_COMPLETE_FILE
from toscarizer.fdl import generate_fdl
from toscarizer.docker_images import generate_dockerfiles, build_and_push, generate_containers
from toscarizer.im_tosca import gen_tosca_yaml


@click.group()
def toscarizer_cli():
    pass


@click.command()
@click.option("--application_dir", help="Path to the AI-SPRINT application.", required=True)
@click.option("--username", help="Username to login to the docker registry.", type=str, required=True)
@click.option("--password", help="Pasword to login to the docker registry.", type=str, required=True)
@click.option("--registry", help="Registry to push the generated docker images.", type=str, required=True)
@click.option("--dry-run", help="Registry to push the generated docker images.", default=False, is_flag=True)
def docker(application_dir, username, password, registry, dry_run):
    resources = parse_resources("%s/%s" % (application_dir, RESOURCES_FILE))
    with open("%s/%s" % (application_dir, COMPONENT_FILE), 'r') as f:
        components = yaml.safe_load(f)
    dockerfiles = generate_dockerfiles(components, resources)
    docker_images = build_and_push(registry, dockerfiles, username, password, not dry_run, not dry_run)
    print("Docker images generated and pushed to the registry.")
    generate_containers(docker_images, "%s/%s" % (application_dir, CONTAINERS_FILE))
    print("DONE. %s file created with new image URLs." % CONTAINERS_FILE)


@click.command()
@click.option("--design-dir", help="Path to the design of the AI-SPRINT application.", type=str, required=True)
def fdl(design_dir):
    resources = parse_resources("%s/%s" % (design_dir, RESOURCES_FILE))
    dag = parse_dag("%s/%s" % (design_dir, DAG_FILE))
    fdl = generate_fdl(dag, resources)
    fdl_file = "%s/oscar/fdl.yaml" % design_dir
    with open(fdl_file, 'w+') as f:
        yaml.safe_dump(fdl, f, indent=2)
    print("DONE. FDL file %s has been generated." % fdl_file)


@click.command()
@click.option("--application_dir", help="Path to the AI-SPRINT application.", required=True)
def tosca(application_dir):
    toscas = gen_tosca_yaml("%s/%s" % (application_dir, RESOURCES_COMPLETE_FILE))
    for cl, tosca in toscas.items():
        tosca_file = "%s/deployments/optimal_deployment/im/%s.yaml" % (application_dir, cl)
        with open(tosca_file, 'w+') as f:
            yaml.safe_dump(tosca, f, indent=2)
        print("DONE. TOSCA file %s has been generated for Computational Layer: %s." % (tosca_file, cl))


toscarizer_cli.add_command(docker)
toscarizer_cli.add_command(fdl)
toscarizer_cli.add_command(tosca)

if __name__ == '__main__':
    toscarizer_cli()
