# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
from setuptools import setup

version = '0.1'

# get documentation from the README
try:
    here = os.path.dirname(os.path.abspath(__file__))
    description = file(os.path.join(here, 'README.md')).read()
except (OSError, IOError):
    description = ''

# dependencies
deps = ['gaiatest-v2.1',
        'mozdevice>=0.34',
        'mozlog>=1.4',
        'mutagen']

setup(name='b2gpopulate-v2.1',
      version=version,
      description="Content population tool for B2G",
      long_description=description,
      classifiers=[],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='mozilla b2g boot2gecko firefoxos populate',
      author='Dave Hunt',
      author_email='dhunt@mozilla.com',
      url='https://github.com/mozilla/b2gpopulate',
      license='MPL',
      packages=['b2gpopulate'],
      package_data={'b2gpopulate': [
          'resources/contactsDb.zip',
          'resources/dialerDb.zip',
          'resources/smsAttachments.zip',
          'resources/smsDb.zip',
          'resources/IMG_0001.jpg',
          'resources/MUS_0001.mp3',
          'resources/VID_0001.3gp']},
      include_package_data=True,
      zip_safe=False,
      entry_points="""
        [console_scripts]
        b2gpopulate = b2gpopulate.b2gpopulate:cli
      """,
      install_requires=deps)
