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

But TOSCARIZER requires docker to build and push the application images
so it must be installed to enable the full operation of the tool.

### Step2: Try --help

```sh
toscarizer --help
```

### Step3: Build and push the container images needed by each component of the application

This step requires `docker` installed. See how to install it [here](https://docs.docker.com/engine/install/).
In case that any of the images will run on an ARM platform, support multiarch
docker builds must be installed also. See how to configure it [here](https://docs.docker.com/desktop/multi-arch/).

```sh
toscarizer docker --registry registry.gitlab.polimi.it \
                  --registry_folder /ai-sprint \
                  --username user \
                  --password pass \
                  --application_dir app
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

It has also the option to prepare the OSCAR clusters to be elastic,
use the `--elastic` option setting the maximum number of nodes to set.

```sh
toscarizer tosca --application_dir app --optimal --elastic 10
```

In the elastic cases it needs the [IM authentication file](https://imdocs.readthedocs.io/en/latest/client.html#auth-file).
The default location is ``app/im/auth.dat`` or you can set another one using
`--im_auth` option.

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
`im.grycap.net` you should contact the authors to get a set of valid
credentials. Otherwise you can change the `domain` input value in the
`oscar.yaml` template and then use your own credentials.

But you can also specify the URL of another IM endpoint, an specific IM
authentication file, and even the set of TOSCA files to deploy.

```sh
toscarizer deploy --im_url http://someim.com \
                  --im_auth auth.dat \
                  --tosca_file some_path/tosca1.yaml \
                  --tosca_file some_path/tosca1.yaml
```

It will return in the standard output a YAML formatted output with the name
of each yaml file with the infrastructure ID generated or the error message
returned.

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
