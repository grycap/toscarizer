import click
import yaml
import sys
import os
import glob

sys.path.append(".")

from toscarizer.utils import (DEPLOYMENTS_FILE,
                              RESOURCES_FILE,
                              COMPONENT_FILE,
                              CONTAINERS_FILE,
                              RESOURCES_COMPLETE_FILE,
                              BASE_DAG_FILE,
                              OPTIMAL_DAG_FILE,
                              PHYSICAL_NODES_FILE,
                              parse_dag,
                              parse_resources)
from toscarizer.fdl import generate_fdl
from toscarizer.docker_images import generate_dockerfiles, build_and_push, generate_containers
from toscarizer.im_tosca import gen_tosca_yamls
from toscarizer.deploy import deploy as deploy_tosca
from toscarizer.delete import destroy


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
    resources = parse_resources("%s/%s" % (application_dir, RESOURCES_FILE),
                                "%s/%s" % (application_dir, DEPLOYMENTS_FILE))
    with open("%s/%s" % (application_dir, COMPONENT_FILE), 'r') as f:
        components = yaml.safe_load(f)
    dockerfiles = generate_dockerfiles(application_dir, components, resources)
    docker_images = build_and_push(registry, registry_folder, dockerfiles,
                                   username, password, not dry_run, not dry_run)
    print("Docker images generated and pushed to the registry.")
    generate_containers(docker_images, "%s/%s" % (application_dir, CONTAINERS_FILE))
    print("DONE. %s/%s file created with new image URLs." % (application_dir, CONTAINERS_FILE))


@click.command()
@click.option("--application_dir", help="Path to the AI-SPRINT application.", required=True)
@click.option('--base', is_flag=True, help="Generates base FDL for base case", default=False)
@click.option('--optimal', is_flag=True, help="Generates the optimal FDL", default=False)
def fdl(application_dir, base, optimal):
    if not base and not optimal:
        print("--base or --optimal options must be set.")
        sys.exit(1)

    if optimal:
        tosca_dir = "%s/aisprint/deployments/optimal_deployment/im" % application_dir
    else:
        tosca_dir = "%s/aisprint/deployments/base/im" % application_dir

    tosca_files = glob.glob("%s/*.yaml" % tosca_dir)
    if not tosca_files:
        print("No TOSCA files. Please perform the tosca operation first.")
        sys.exit(-1)
    fdl = generate_fdl(tosca_files)

    if optimal:
        fdl_file = "%s/aisprint/deployments/optimal_deployment/oscar/fdl.yaml" % application_dir
    else:
        fdl_file = "%s/aisprint/deployments/base/oscar/fdl.yaml" % application_dir

    with open(fdl_file, 'w+') as f:
        yaml.safe_dump(fdl, f, indent=2)
    print("DONE. FDL file %s has been generated." % fdl_file)


@click.command()
@click.option("--application_dir", help="Path to the AI-SPRINT application.", default=None)
@click.option('--base', is_flag=True, help="Generates base TOSCA file for base case", default=False)
@click.option('--optimal', is_flag=True, help="Generates the optimal TOSCA file", default=False)
def tosca(application_dir, base, optimal):
    if not base and not optimal:
        print("--base or --optimal options must be set.")
        sys.exit(1)

    with open("%s/%s" % (application_dir, CONTAINERS_FILE), 'r') as f:
        containers = yaml.safe_load(f)

    if base:
        dag = parse_dag("%s/%s" % (application_dir, BASE_DAG_FILE))
        deployments_file = "%s/%s" % (application_dir, DEPLOYMENTS_FILE)
        resources = parse_resources("%s/%s" % (application_dir, RESOURCES_FILE),
                                    "%s/%s" % (application_dir, DEPLOYMENTS_FILE))
        resources_file = "%s/%s" % (application_dir, RESOURCES_FILE)
    else:
        dag = parse_dag("%s/%s" % (application_dir, OPTIMAL_DAG_FILE))
        deployments_file = "%s/%s" % (application_dir, RESOURCES_COMPLETE_FILE)
        resources = parse_resources("%s/%s" % (application_dir, RESOURCES_COMPLETE_FILE),
                                    "%s/%s" % (application_dir, RESOURCES_COMPLETE_FILE))
        resources_file = "%s/%s" % (application_dir, RESOURCES_COMPLETE_FILE)

    toscas = gen_tosca_yamls(dag, containers, resources, resources_file, deployments_file,
                             "%s/%s" % (application_dir, PHYSICAL_NODES_FILE))
    for cl, tosca in toscas.items():
        if optimal:
            tosca_file = "%s/aisprint/deployments/optimal_deployment/im/%s.yaml" % (application_dir, cl)
        else:
            tosca_file = "%s/aisprint/deployments/base/im/%s.yaml" % (application_dir, cl)
        with open(tosca_file, 'w+') as f:
            yaml.safe_dump(tosca, f, indent=2)
        print("DONE. TOSCA file %s has been generated for Component: %s." % (tosca_file, cl))


@click.command()
@click.option('--im_url', required=False, default="https://im.egi.eu/im")
@click.option('--im_auth', required=False)
@click.option('--verify', required=False, default=False)
@click.option("--application_dir", help="Path to the AI-SPRINT application.", required=False, default=None)
@click.option('--base', is_flag=True, help="Deploys base case infrastructure", required=False, default=False)
@click.option('--optimal', is_flag=True, help="Deploys optimal case infrastructure", required=False, default=False)
@click.option('--tosca_file', multiple=True, required=False)
def deploy(im_url, im_auth, verify, application_dir, base, optimal, tosca_file):

    dag = None
    if application_dir:
        if not base and not optimal:
            print("--base or --optimal options must be set.")
            sys.exit(1)
        if tosca_file:
            print("--application_dir option set: --tosca_file will be ignored.")

        if optimal:
            tosca_dir = "%s/aisprint/deployments/optimal_deployment/im" % application_dir
            dag = parse_dag("%s/%s" % (application_dir, OPTIMAL_DAG_FILE))
        else:
            tosca_dir = "%s/aisprint/deployments/base/im" % application_dir
            dag = parse_dag("%s/%s" % (application_dir, BASE_DAG_FILE))
        tosca_file = glob.glob("%s/*.yaml" % tosca_dir)

    elif not tosca_file:
        print("--application_dir or --tosca_file options must be set.")
        sys.exit(1)

    if not im_auth and application_dir:
        im_auth = "%s/im/auth.dat" % application_dir
    if not os.path.isfile(im_auth):
        print("IM auth data does not exit." % im_auth)
        sys.exit(-1)

    with open(im_auth, 'r') as f:
        auth_data = f.read().replace("\n", "\\n")

    res = deploy_tosca(tosca_file, auth_data, im_url, verify, dag)
    print(yaml.safe_dump(res, indent=2))

    im_infras = "%s/infras.yaml" % tosca_dir
    with open(im_infras, 'w+') as f:
        yaml.safe_dump(res, f, indent=2)


@click.command()
@click.option('--im_auth', required=False)
@click.option('--verify', required=False, default=False)
@click.option("--application_dir", help="Path to the AI-SPRINT application.", default=None)
@click.option('--base', is_flag=True, help="Generates base TOSCA file for base case", default=False)
@click.option('--optimal', is_flag=True, help="Generates the optimal TOSCA file", default=False)
def delete(im_auth, verify, application_dir, base, optimal):
    im_auth = "%s/im/auth.dat" % application_dir

    with open(im_auth, 'r') as f:
        auth_data = f.read().replace("\n", "\\n")

    if optimal:
        im_infras_path = "%s/aisprint/deployments/optimal_deployment/im/infras.yaml" % application_dir
    else:
        im_infras_path = "%s/aisprint/deployments/base/im/infras.yaml" % application_dir

    with open(im_infras_path, 'r') as f:
        im_infras = yaml.safe_load(f)

    success = destroy(im_infras, auth_data, verify)
    if success:
        os.unlink(im_infras_path)


toscarizer_cli.add_command(docker)
toscarizer_cli.add_command(fdl)
toscarizer_cli.add_command(tosca)
toscarizer_cli.add_command(deploy)
toscarizer_cli.add_command(delete)

if __name__ == '__main__':
    toscarizer_cli()
