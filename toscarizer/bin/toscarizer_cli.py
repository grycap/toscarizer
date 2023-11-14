# Copyright (C) GRyCAP - I3M - UPV
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
                              RELATIVE_DAG_FILE,
                              PHYSICAL_NODES_FILE,
                              QOS_CONSTRAINTS_FILE,
                              OPTIMAL_QOS_CONSTRAINTS_FILE,
                              RELATIVE_QOS_CONSTRAINTS_FILE,
                              parse_dag,
                              parse_resources,
                              get_base_deployment_name)
from toscarizer.fdl import generate_fdl
from toscarizer.docker_images import generate_dockerfiles, build_and_push, generate_containers
from toscarizer.im_tosca import gen_tosca_yamls
from toscarizer.deploy import deploy as deploy_tosca
from toscarizer.delete import destroy
from toscarizer.outputs import get_outputs

yaml.Dumper.ignore_aliases = lambda *args: True


@click.group()
def toscarizer_cli():
    pass


@click.command()
@click.option("--application_dir", help="Path to the AI-SPRINT application.", required=True)
@click.option("--registry", help="Registry to push the generated docker images.", type=str, required=True)
@click.option("--registry_folder", help="Registry folder to push the generated docker images.", type=str, default="/")
@click.option("--base_image", help="Base image for the docker images.", type=str,
              default="registry.gitlab.polimi.it/ai-sprint/toscarizer/ai-sprint-base")
@click.option("--ecr", help="AWS ECR repository URL.", type=str, default=None)
@click.option("--dry-run", help="Registry to push the generated docker images.", default=False, is_flag=True)
def docker(application_dir, registry, registry_folder, base_image, ecr, dry_run):
    resources = parse_resources("%s/%s" % (application_dir, RESOURCES_FILE),
                                "%s/%s" % (application_dir, DEPLOYMENTS_FILE))
    with open("%s/%s" % (application_dir, COMPONENT_FILE), 'r') as f:
        components = yaml.safe_load(f)
    dockerfiles = generate_dockerfiles(base_image, application_dir, components, resources)
    docker_images = build_and_push(registry, registry_folder, dockerfiles,
                                   ecr, not dry_run, not dry_run)
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
        os.makedirs("%s/aisprint/deployments/optimal_deployment/oscar/" % application_dir, exist_ok=True)
        fdl_file = "%s/aisprint/deployments/optimal_deployment/oscar/fdl.yaml" % application_dir
    else:
        os.makedirs("%s/aisprint/deployments/base/oscar/" % application_dir, exist_ok=True)
        fdl_file = "%s/aisprint/deployments/base/oscar/fdl.yaml" % application_dir

    with open(fdl_file, 'w+') as f:
        yaml.safe_dump(fdl, f, indent=2)
    print("DONE. FDL file %s has been generated." % fdl_file)


@click.command()
@click.option("--application_dir", help="Path to the AI-SPRINT application.", default=None)
@click.option('--base', is_flag=True, help="Generates base TOSCA file for base case", default=False)
@click.option('--optimal', is_flag=True, help="Generates the optimal TOSCA file", default=False)
@click.option('--elastic', help="Set max number of nodes to deploy the OSCAR cluster as elastic", default=0)
@click.option('--im_auth', help="Set the IM auth file path", required=False)
@click.option('--domain', help="Set the OSCAR clusters DNS domain", required=False)
@click.option('--influxdb_url', help="Set InfluxDB URL", required=False, default='https://influx.oncloudandheat.com/')
@click.option('--influxdb_token', help="Set InfluxDB API token", required=False, default='')
@click.option('--registry_server', help="Set a private registry server", required=False, default='')
@click.option('--registry_username', help="Set a private registry username", required=False, default='')
@click.option('--registry_password', help="Set a private registry password", required=False, default='')
def tosca(application_dir, base, optimal, elastic, im_auth, domain, influxdb_url,
          influxdb_token, registry_server, registry_username, registry_password):
    if not base and not optimal:
        print("--base or --optimal options must be set.")
        sys.exit(1)

    auth_data = None
    if elastic:
        if not im_auth and application_dir:
            im_auth = "%s/im/auth.dat" % application_dir
        if not os.path.isfile(im_auth):
            print("IM auth data does not exit." % im_auth)
            sys.exit(-1)
        with open(im_auth, 'r') as f:
            auth_data = f.read().replace("\n", "\\n")

    if base:
        app_name, dag = parse_dag("%s/%s" % (application_dir, BASE_DAG_FILE))
        deployments_file = "%s/%s" % (application_dir, DEPLOYMENTS_FILE)
        resources_file = "%s/%s" % (application_dir, RESOURCES_FILE)
        qos_contraints_file = "%s/%s" % (application_dir, QOS_CONSTRAINTS_FILE)
    else:
        deployments_file = "%s/%s" % (application_dir, RESOURCES_COMPLETE_FILE)
        resources_file = "%s/%s" % (application_dir, RESOURCES_COMPLETE_FILE)
        base_deployment_name = get_base_deployment_name(deployments_file)
        if base_deployment_name:
            app_name, dag = parse_dag("%s/%s" % (application_dir, RELATIVE_DAG_FILE % base_deployment_name))
            qos_contraints_file = "%s/%s" % (application_dir, RELATIVE_QOS_CONSTRAINTS_FILE % base_deployment_name)
        else:
            app_name, dag = parse_dag("%s/%s" % (application_dir, OPTIMAL_DAG_FILE))
            qos_contraints_file = "%s/%s" % (application_dir, OPTIMAL_QOS_CONSTRAINTS_FILE)

    secret = None
    if registry_server and registry_username and registry_password:
        secret = {
            "name": "private_registry",
            "server": registry_server,
            "username": registry_username,
            "password": registry_password
        }

    toscas = gen_tosca_yamls(app_name, dag, resources_file, deployments_file,
                             "%s/%s" % (application_dir, PHYSICAL_NODES_FILE),
                             elastic, auth_data, domain, influxdb_url, influxdb_token,
                             qos_contraints_file, "%s/%s" % (application_dir, CONTAINERS_FILE),
                             secret)
    for cl, tosca in toscas.items():
        if optimal:
            os.makedirs("%s/aisprint/deployments/optimal_deployment/im/" % application_dir, exist_ok=True)
            tosca_file = "%s/aisprint/deployments/optimal_deployment/im/%s.yaml" % (application_dir, cl)
        else:
            os.makedirs("%s/aisprint/deployments/base/im/" % application_dir, exist_ok=True)
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
            deployments_file = "%s/%s" % (application_dir, RESOURCES_COMPLETE_FILE)
            base_deployment_name = get_base_deployment_name(deployments_file)
            if base_deployment_name:
                _, dag = parse_dag("%s/%s" % (application_dir, RELATIVE_DAG_FILE % base_deployment_name))
            else:
                _, dag = parse_dag("%s/%s" % (application_dir, OPTIMAL_DAG_FILE))
        else:
            tosca_dir = "%s/aisprint/deployments/base/im" % application_dir
            _, dag = parse_dag("%s/%s" % (application_dir, BASE_DAG_FILE))
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


@click.command()
@click.option('--im_auth', required=False)
@click.option('--verify', required=False, default=False)
@click.option("--application_dir", help="Path to the AI-SPRINT application.", default=None)
@click.option('--base', is_flag=True, help="Generates base TOSCA file for base case", default=False)
@click.option('--optimal', is_flag=True, help="Generates the optimal TOSCA file", default=False)
def outputs(im_auth, verify, application_dir, base, optimal):
    im_auth = "%s/im/auth.dat" % application_dir

    with open(im_auth, 'r') as f:
        auth_data = f.read().replace("\n", "\\n")

    if optimal:
        im_infras_path = "%s/aisprint/deployments/optimal_deployment/im/infras.yaml" % application_dir
    else:
        im_infras_path = "%s/aisprint/deployments/base/im/infras.yaml" % application_dir

    with open(im_infras_path, 'r') as f:
        im_infras = yaml.safe_load(f)

    outputs = get_outputs(im_infras, auth_data, verify)
    print(yaml.dump(outputs, indent=2))


toscarizer_cli.add_command(docker)
toscarizer_cli.add_command(fdl)
toscarizer_cli.add_command(tosca)
toscarizer_cli.add_command(deploy)
toscarizer_cli.add_command(delete)
toscarizer_cli.add_command(outputs)

if __name__ == '__main__':
    toscarizer_cli()
