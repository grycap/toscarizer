from setuptools import setup

setup(
    name='oscariser',
    version='0.1',
    author='Miguel Caballer',
    long_description='OSCARISER',
    url='https://gitlab.polimi.it/grycap/oscariser',
    python_requires='>=3.7',
    packages = ["oscariser", "oscariser.bin"],
    package_dir = {"oscariser": "oscariser",
                   "oscariser.bin": "oscariser/bin  "},
    install_requires=['PyYAML', 'networkx', 'docker'],
    entry_points={
        'console_scripts': [
            'oscariser=oscariser.bin.oscariser_cli:oscariser_cli',
        ]
    }
)
