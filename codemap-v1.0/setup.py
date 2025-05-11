from setuptools import setup, find_packages
import os
import sys

sys.path.insert(0, os.path.abspath('.'))

setup(
    name="codemap",
    version="1.0.0",
    description="A file tree explorer for code visualization and management",
    author="CodeMap Team",
    packages=find_packages() + ['config', 'core', 'ui'],
    package_dir={
        'config': 'config',
        'core': 'core',
        'ui': 'ui'
    },
    py_modules=['main'],
    install_requires=[
        "tiktoken",
        "pygments",
        "keyboard",
    ],
    entry_points={
        'console_scripts': [
            'codemap=main:run',
        ],
    },
    python_requires='>=3.6',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],

)
