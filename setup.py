# Copyright (C) GRyCAP - I3M - UPV
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
