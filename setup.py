#
#  Copyright 2017 Netflix, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
  name = 'pyconductor',
  packages = ['pyconductor'], # this must be the same as the name above
  version = '0.1.3',
  description = 'Conductor python client',
  long_description=long_description,
  long_description_content_type="text/markdown",
  author = 'Samarth Hattangady',
  author_email = 'samhattangady@gmail.com',
  url = 'https://github.com/skylarkdrones/pyconductor',
  keywords = ['netflix', 'conductor', 'pyconductor'],
  license = 'Apache 2.0',
  install_requires = [
    'requests',
  ],
)
