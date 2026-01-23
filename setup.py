#!/usr/bin/env python3
"""
Setup script for ReconDesk
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_file(filename):
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, filename), encoding='utf-8') as f:
        return f.read()

setup(
    name='recondesk',
    version='1.0.0',
    description='A reconnaissance and information gathering CLI tool',
    long_description=read_file('README.md') if os.path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    author='ReconDesk Team',
    license='GPL-3.0',
    url='https://github.com/yourusername/recondesk',
    packages=find_packages(),
    install_requires=[
        'inquirer>=3.1.3',
        'blessed>=1.20.0',
        'readchar>=4.0.5',
    ],
    entry_points={
        'console_scripts': [
            'recondesk=recondesk.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Security',
        'Topic :: System :: Networking',
    ],
    python_requires='>=3.8',
    keywords='reconnaissance recon security information-gathering cli',
)
