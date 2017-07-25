import sys
import setuptools

if sys.version_info < (2, 7):
    raise RuntimeError('python 2.7 or greater is required')

setuptools.setup(
    name='monitor',
    version='0.0.1',
    description='Real-time monitor for access log',
    packages=setuptools.find_packages(),
    install_requires=[
        #'supervisor>=3.1.3',
    ],
    dependency_links=[
    ],
    entry_points={
        'console_scripts': [
        ],
    },
)
