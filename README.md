# TOSCARIZER

## Quick-Start

### Step1: Install TOSCARIZER 
```
git clone https://gitlab.polimi.it/grycap/toscarizer.git
cd toscarizer
python3 -m pip install . 
```

### Step2: Try --help 
```
toscarizer --help
```

### Step3: Build and push the container images needed by each component of the application
```
toscarizer docker --registry registry.gitlab.polimi.it/ai-sprint --username user --password pass --application_dir app
```

### Step4: Generate the corresponding OSCAR FDL files

Generate the FDL for the base case.

```
toscarizer fdl --application_dir app --base
```

Generate the FDL for the optima case.

```
toscarizer fdl --application_dir app --optimal
```

### Step5: Generate the corresponding TOSCA YAML files

Generate the TOSCA IM input files for the optimal case:

```
toscarizer tosca --application_dir app
```

Generate the TOSCA IM input files for a generic resorces file.

```
toscarizer tosca --resource_file some_path/resources.yaml
```

In both cases if some resources are of type ``PhysicalAlreadyProvisioned`` an extra file with the needed information to connect with this resources (IP, and SSH auth data) is needed. In case of using application_dir it is expected in the app common_config directory with name ``physical_nodes.yaml`` in case of using resource_file, it must me set also as parameter in the command.

```
toscarizer tosca --resource_file some_path/resources.yaml --phys_file some_path/physical_nodes.yaml
```


### Step6: Deploy TOSCA YAML files

```
toscarizer deploy --im_url http://someim.com --im_auth auth.dat --tosca_file some_path/tosca1.yaml --tosca_file some_path/tosca1.yaml 
```