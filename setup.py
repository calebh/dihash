from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
   name='dihash',
   version='2.1',
   description='Python implementation of various directed graph hashing functions.',
   license='MIT',
   long_description=long_description,
   author='Caleb Helbling',
   author_email='caleb.helbling@yahoo.com',
   packages=['dihash'],
   install_requires=['pynauty', 'networkx']
)