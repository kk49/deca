from setuptools import setup, find_packages

setup(
    name='deca',
    version='0.1dev',
    description='Tools for ...',
    # packages=['deca', 'deca.cmds', 'deca.gui', ],
    packages=find_packages(),
    url='http://github.com/kk49/deca',
    license='MIT',
    data_files=[('./', ['./deca/process_image.so'])],
)
