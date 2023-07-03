from setuptools import setup, find_packages

setup(
    name='toscarizer',
    version='0.3',
    author='Miguel Caballer',
    long_description='TOSCARIZER',
    url='https://gitlab.polimi.it/grycap/toscarizer',
    python_requires='>=3.7',
    package_data={"": ['Dockerfile.template', 'Dockerfile.aws.template', 'script.sh', 'start.sh', 'oscar.yaml',
                       'oscar_wn.yaml', 'oscar_wn_elastic.yaml', 'oscar_elastic.yaml', 'telegraf.conf']},
    packages=find_packages(),
    install_requires=['PyYAML', 'networkx', 'docker', 'requests', 'click'],
    entry_points={
        'console_scripts': [
            'toscarizer=toscarizer.bin.toscarizer_cli:toscarizer_cli',
        ]
    }
)
