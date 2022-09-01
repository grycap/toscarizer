import click
import yaml
import sys
import requests
import os.path

sys.path.append(".")

from toscarizer.utils import DEPLOYMENTS_FILE, parse_dag, parse_resources, RESOURCES_FILE, COMPONENT_FILE, CONTAINERS_FILE, RESOURCES_COMPLETE_FILE, BASE_DAG_FILE, OPTIMAL_DAG_FILE, PHYSICAL_NODES_FILE
from toscarizer.fdl import generate_fdl
from toscarizer.docker_images import generate_dockerfiles, build_and_push, generate_containers
from toscarizer.im_tosca import gen_tosca_yamls


@click.group()
def toscarizer_cli():
    pass


@click.command()
@click.option("--application_dir", help="Path to the AI-SPRINT application.", required=True)
@click.option("--username", help="Username to login to the docker registry.", type=str, required=True)
@click.option("--password", help="Pasword to login to the docker registry.", type=str, required=True)
@click.option("--registry", help="Registry to push the generated docker images.", type=str, required=True)
@click.option("--registry_folder", help="Registry folder to push the generated docker images.", type=str, default="/")
@click.option("--dry-run", help="Registry to push the generated docker images.", default=False, is_flag=True)
def docker(application_dir, username, password, registry, registry_folder, dry_run):
    resources = parse_resources("%s/%s" % (application_dir, RESOURCES_FILE), "%s/%s" % (application_dir, DEPLOYMENTS_FILE))
    with open("%s/%s" % (application_dir, COMPONENT_FILE), 'r') as f:
        components = yaml.safe_load(f)
    dockerfiles = generate_dockerfiles(application_dir, components, resources)
    docker_images = build_and_push(registry, registry_folder, dockerfiles, username, password, not dry_run, not dry_run)
    print("Docker images generated and pushed to the registry.")
    generate_containers(docker_images, "%s/%s" % (application_dir, CONTAINERS_FILE))
    print("DONE. %s file created with new image URLs." % CONTAINERS_FILE)


@click.command()
@click.option("--application_dir", help="Path to the AI-SPRINT application.", required=True)
@click.option('--base', is_flag=True, help="Generates base FDL for OSCAR-P", default=False)
@click.option('--optimal', is_flag=True, help="Generates the optimal FDL", default=False)
def fdl(application_dir, base, optimal):
    if not base and not optimal:
        print("--base or --optimal options must be set.")
        sys.exit(1)

    with open("%s/%s" % (application_dir, CONTAINERS_FILE), 'r') as f:
        containers = yaml.safe_load(f)

    if base:
        resources = parse_resources("%s/%s" % (application_dir, RESOURCES_FILE), "%s/%s" % (application_dir, DEPLOYMENTS_FILE))
        dag = parse_dag("%s/%s" % (application_dir, BASE_DAG_FILE))
        fdl = generate_fdl(dag, resources, containers)
        fdl_file = "%s/aisprint/deployments/base/oscar/fdl.yaml" % application_dir
        with open(fdl_file, 'w+') as f:
            yaml.safe_dump(fdl, f, indent=2)
        print("DONE. FDL file %s has been generated." % fdl_file)

    if optimal:
        resources = parse_resources("%s/%s" % (application_dir, RESOURCES_COMPLETE_FILE), "%s/%s" % (application_dir, DEPLOYMENTS_FILE))
        dag = parse_dag("%s/%s" % (application_dir, OPTIMAL_DAG_FILE))
        fdl = generate_fdl(dag, resources, containers)
        fdl_file = "%s/aisprint/deployments/optimal_deployment/oscar/fdl.yaml" % application_dir
        with open(fdl_file, 'w+') as f:
            yaml.safe_dump(fdl, f, indent=2)
        print("DONE. FDL file %s has been generated." % fdl_file)


@click.command()
@click.option("--application_dir", help="Path to the AI-SPRINT application.", default=None)
@click.option("--resource_file", help="Path to resource file.", default=None)
@click.option("--phys_file", help="Path to physical nodes file.", default=None)
def tosca(application_dir, resource_file, phys_file):
    if not resource_file:
        if not application_dir:
            print("--application_dir or --resource_file options must be set.")
            sys.exit(1)
        resource_file = "%s/%s" % (application_dir, RESOURCES_COMPLETE_FILE)
    if not phys_file:
        if application_dir:
            phys_file = "%s/%s" % (application_dir, PHYSICAL_NODES_FILE)
            if not os.path.isfile(phys_file):
                phys_file = None

    toscas = gen_tosca_yamls(resource_file, phys_file)
    for cl, tosca in toscas.items():
        if application_dir:
            tosca_file = "%s/aisprint/deployments/optimal_deployment/im/%s.yaml" % (application_dir, cl)
        else:
            tosca_file = "%s/%s.yaml" % (os.path.dirname(resource_file), cl)
        with open(tosca_file, 'w+') as f:
            yaml.safe_dump(tosca, f, indent=2)
        print("DONE. TOSCA file %s has been generated for Computational Layer: %s." % (tosca_file, cl))


@click.command()
@click.option('--im_url', required=True)
@click.option('--im_auth', required=True)
@click.option('--verify', required=False, default=False)
@click.option('--tosca_file', multiple=True, required=True)
def deploy(im_url, im_auth, verify, tosca_file):
    with open(im_auth, 'r') as f:
        auth_data = f.read().replace("\n", "\\n")

    headers = {"Authorization": auth_data}
    headers["Content-Type"] = "text/yaml"
    url = "%s/infrastructures" % im_url
    res = {}
    for file in tosca_file:
        with open(file, 'r') as f:
            tosca_data = f.read()
        resp = requests.request("POST", url, verify=verify, headers=headers, data=tosca_data)
        success = resp.status_code == 200
        res[file] = {}
        if success:
            res[file]["infId"] = resp.text
        else:
            res[file]["error"] = resp.text

    print(yaml.safe_dump(res, indent=2))


toscarizer_cli.add_command(docker)
toscarizer_cli.add_command(fdl)
toscarizer_cli.add_command(tosca)
toscarizer_cli.add_command(deploy)

if __name__ == '__main__':
    toscarizer_cli()
