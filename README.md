# TOSCARIZER

## Quick-Start

### Step1: Install TOSCARIZER

```sh
git clone https://gitlab.polimi.it/grycap/toscarizer.git
cd toscarizer
python3 -m pip install . 
```

### Step2: Try --help

```sh
toscarizer --help
```

### Step3: Build and push the container images needed by each component of the application

```sh
toscarizer docker --registry registry.gitlab.polimi.it --registry_folder /ai-sprint --username user --password pass --application_dir app
```

### Step4: Generate the corresponding OSCAR FDL files

Generate the FDL for the base case.

```sh
toscarizer fdl --application_dir app --base
```

Generate the FDL for the optimal case.

```sh
toscarizer fdl --application_dir app --optimal
```

### Step5: Generate the corresponding TOSCA YAML files

Generate the TOSCA IM input files for the base case:

```sh
toscarizer tosca --application_dir app --base
```

Generate the TOSCA IM input files for the optimal case:

```sh
toscarizer tosca --application_dir app --optimal
```

In both cases if some resources are of type ``PhysicalAlreadyProvisioned`` an extra file with the needed information to connect with this resources (IP, and SSH auth data) is needed. It is expected in the app common_config directory with name ``physical_nodes.yaml``. See [here](app/common_config/physical_nodes.yaml) an example of the format.

### Step6: Deploy TOSCA YAML files

```sh
toscarizer deploy --im_url http://someim.com --im_auth auth.dat --tosca_file some_path/tosca1.yaml --tosca_file some_path/tosca1.yaml 
```
