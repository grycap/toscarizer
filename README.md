# OSCARISER

## Quick-Start

### Step1: Install OSCARISER 
```
git clone https://gitlab.polimi.it/grycap/oscariser.git
cd oscariser
python3 -m pip install . 
```

### Step2: Try --help 
```
oscariser --help
```

### Step3: Build and push the container images needed by each component of the application
```
oscariser docker --registry registry.gitlab.polimi.it/ai-sprint --username user --password pass --design-dir design_example
```

### Step4: Generate the corresponding OSCAR FDL files
```
oscariser fdl --design-dir design_example
```

### Step5: Generate the corresponding TOSCA YAML files
```
oscariser tosca --design-dir design_example
```