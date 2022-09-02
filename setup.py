from setuptools import setup

setup(
    name='toscarizer',
    version='0.1',
    author='Miguel Caballer',
    long_description='TOSCARIZER',
    url='https://gitlab.polimi.it/grycap/toscarizer',
    python_requires='>=3.7',
    packages=["toscarizer", "toscarizer.bin"],
    package_dir={"toscarizer": "toscarizer",
                 "toscarizer.bin": "toscarizer/bin  "},
    install_requires=['PyYAML', 'networkx', 'docker', 'requests'],
    entry_points={
        'console_scripts': [
            'toscarizer=toscarizer.bin.toscarizer_cli:toscarizer_cli',
        ]
    }
)
