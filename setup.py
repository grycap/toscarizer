from setuptools import setup, find_packages

setup(
    name='toscarizer',
    version='0.1',
    author='Miguel Caballer',
    long_description='TOSCARIZER',
    url='https://gitlab.polimi.it/grycap/toscarizer',
    python_requires='>=3.7',
    package_data={"": ['Dockerfile.template', 'script.sh', 'oscar.yaml', 'oscar_wn.yaml']},
    packages = find_packages(),
    install_requires=['PyYAML', 'networkx', 'docker', 'requests', 'click'],
    entry_points={
        'console_scripts': [
            'toscarizer=toscarizer.bin.toscarizer_cli:toscarizer_cli',
        ]
    }
)