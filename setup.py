
import os
from distutils.core import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='stresslib',
    version='0.1',
    packages=['stresslib'],
    author='Alvaro Leiva',
    author_email='aleivag@gmail.com',
    url='https://github.com/aleivag/stress',
    #download_url='https://github.com/aleivag/stress/releases/tarball/v0.1',
    classifiers=["Development Status :: 3 - Alpha", "Topic :: Utilities"],
    keywords=['monitoring', 'rum', 'pingdom'],
    description='A simple stress API to run multipless commands',
    #long_description=read('README.rst'),
    license='MIT'
)
