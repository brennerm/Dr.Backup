from setuptools import setup

setup(
    name='dr-backup',
    version='0.1',
    packages=['dr_backup'],
    entry_points={
        'console_scripts': [
            'dr-backup = dr_backup.__main__:main',
        ],
    },
    url='https://github.com/brennerm/Dr.Backup',
    license='MIT',
    author='brennerm',
    author_email='xamrennerb@gmail.com',
    description='Backup and restore your Docker registries without access to the filesystem.'
)
