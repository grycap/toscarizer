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
```
toscarizer fdl --application_dir app
```

### Step5: Generate the corresponding TOSCA YAML files
```
toscarizer tosca --application_dir app
```