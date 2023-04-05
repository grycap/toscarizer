# TOSCARIZER

## Quick-Start

### Step1: Install TOSCARIZER

```sh
git clone https://gitlab.polimi.it/grycap/toscarizer.git
cd toscarizer
python3 -m pip install . 
```

#### Docker image

A docker image is available with TOSCARIZER and AI-SPRINT Desing tools:
`registry.gitlab.polimi.it/ai-sprint/toscarizer/toscarizer`

You can use it setting the path of you local application directory as in
this example:

```sh
docker run --rm -v local_app_path:/app \
    -ti registry.gitlab.polimi.it/ai-sprint/toscarizer/toscarizer \
    toscarizer tosca --application_dir /app --base
```

In the case of the `docker` operation (Step3) docker is used to build and
push the application images so it must be enabled inside the docker container
to work, as in this example:

```sh
docker run --rm -v local_app_path:/app \
    -v /var/run/docker.sock:/var/run/docker.sock  \
    -v $HOME/.docker/config.json:/root/.docker/config.json \
    -ti registry.gitlab.polimi.it/ai-sprint/toscarizer/toscarizer \
    toscarizer docker --application_dir /app
    ...
```

### Step2: Try --help

```sh
toscarizer --help
```

### Step3: Build and push the container images needed by each component of the application

This step requires `docker` installed. See how to install it [here](https://docs.docker.com/engine/install/).
In case that any of the images will run on an ARM platform, support multiarch
docker builds must be installed also. See how to configure it [here](https://docs.docker.com/desktop/multi-arch/).

First you need to login to the container registry that you will use in the `docker` operation:

```sh
docker login registry.gitlab.polimi.it
```

Also in case that any of the steps uses NativeCloudFunctions (AWS Lambda). You need to also
to login to the ECR repository, using the aws-cli tool (See how to install it
[here](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html)):

```sh
aws ecr get-login-password --region [region] | docker login --username AWS --password-stdin
 XXXXXXXXXXXX.dkr.ecr.[region].amazonaws.com
```

```sh
toscarizer docker --registry registry.gitlab.polimi.it \
                  --registry_folder /ai-sprint \
                  --application_dir app
```

Optionally the `--base_image` parameter can be set to define a different base image
for the generated images. The default value is:
`registry.gitlab.polimi.it/ai-sprint/toscarizer/ai-sprint-base`.

Furthermore in case that any of the steps uses NativeCloudFunctions (AWS Lambda). You need to also
set an existing ECR repository URL:

```sh
toscarizer docker --registry registry.gitlab.polimi.it \
                  --registry_folder /ai-sprint \
                  --application_dir app
                  --ecr XXXXXXXXXXXX.dkr.ecr.[region].amazonaws.com/repo_name
```

### Step4: Generate the corresponding TOSCA YAML files

The `tosca` command uses the files ``templates\*.yaml`` to generate the TOSCA
file for the OSCAR clusters.

Generate the TOSCA IM input files for the base case:

```sh
toscarizer tosca --application_dir app --base
```

Generate the TOSCA IM input files for the optimal case:

```sh
toscarizer tosca --application_dir app --optimal
```

In all cases if some resources are of type ``PhysicalAlreadyProvisioned`` an
extra file with the needed information to connect with this resources (IP, and
SSH auth data or MinIO service info) is needed. It is expected in the app
common_config directory with name ``physical_nodes.yaml``. See [here](app2/common_config/physical_nodes.yaml)
an example of the format.

In the OSCAR configuration a set of valid DNS records are assigned to the nodes to
enable correct and secure external access to the services. A Route53 managed domain
is required to make it work. You can set it with the ``--domain`` parameter
(otherwise the default im.grycap.net will be used):

It has also the option to prepare the OSCAR clusters to be elastic,
use the `--elastic` option setting the maximum number of nodes to set.
This option has a limitation: the WNs of the cluster must have the same
features.

```sh
toscarizer tosca --application_dir app --optimal --elastic 10
```

In the elastic cases it needs the [IM authentication file](https://imdocs.readthedocs.io/en/latest/client.html#auth-file).
The default location is ``app/im/auth.dat`` or you can set another one using
`--im_auth` option.

The generated TOSCA will also set the needed recipes to include the AI-SPRINT
monitoring system. These recipes require to set the central InfluxDB instance URL
(`--influxdb_url` option) and a valid API token (`--influxdb_token` option).

### Step5: Deploy TOSCA YAML files

To deploy the TOSCA files generated for the base case use:

```sh
toscarizer deploy --application_dir app --base
```

To deploy the TOSCA files generated for the optimal case use:

```sh
toscarizer deploy --application_dir app --optimal
```

In both cases it assumes that the [IM authentication file](https://imdocs.readthedocs.io/en/latest/client.html#auth-file)
is located at path ``app/im/auth.dat``. It will use the EGI IM instance (<https://im.egi.eu/im/>).
The auth file must contain not only the InfrastructureManager and the cloud provider
selected, but also some AWS credentials (EC2 type) to manage the DNS domain names
used in the OSCAR TOSCA template. In case of using the default domain value
`im.grycap.net` you should contact the authors to get a set of valid credentials.
Otherwise you have to add some EC2 credentials able to manage the specified domain in AWS Route53.

But you can also specify the URL of another IM endpoint, an specific IM
authentication file, and even the set of TOSCA files to deploy.

```sh
toscarizer deploy --im_url http://someim.com \
                  --im_auth auth.dat \
                  --tosca_file some_path/tosca1.yaml \
                  --tosca_file some_path/tosca1.yaml
```

During deployment process the command will show the IDs of the infrastructures
deployed. You can use this ID to track the status of the deployment. You can
access the IM-Dashboard associated to the IM instance you have specified in
the deploy command ([default one](https://im.egi.eu)), or you can also use the
[IM-Client](https://github.com/grycap/im-client).

At the end it will return in the standard output a YAML formatted output with the name
of each yaml file with the infrastructure ID generated or the error message
returned. In case of unconfigured infrastructures it will also retun the contextualization
log with all the Ansible tasks performed to the infrastructure enabled to debug the error.

### Step6: Get infrastructures Outputs

To get the TOSCA outputs of the infrastructures generated for the base case use:

```sh
toscarizer outputs --application_dir app --base
```

To get the TOSCA outputs of the infrastructures generated for the optimal case use:

```sh
toscarizer outputs --application_dir app --optimal
```

### Step7: Delete infrastructures

To delete the infrastructures generated for the base case use:

```sh
toscarizer delete --application_dir app --base
```

To delete the infrastructures generated for the optimal case use:

```sh
toscarizer delete --application_dir app --optimal
```
