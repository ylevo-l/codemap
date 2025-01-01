from setuptools import setup, find_packages

setup(
    name='codemap',
    version='1.2.0',
    description='Scrollable, interactive ASCII tree view of a directory.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='ylevo-l',
    author_email='slush-nacho-paltry@duck.com',
    url='https://github.com/ylevo-l/codemap',
    license='MIT',
    py_modules=['codemap'],
    install_requires=[
        'windows-curses; platform_system=="Windows"',
    ],
    entry_points={
        'console_scripts': [
            'codemap=codemap:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
