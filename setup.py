from setuptools import find_packages, setup  # type: ignore

VERSION_PATH = 'VERSION'


def find_version():
    with open(VERSION_PATH) as version_file:
        return version_file.read().strip()


dependencies = [
    'Flask==2.2.2',
    'itsdangerous==2.0.1',
    'psutil==5.9.0',
    'docker==5.0.3',
    'sh==1.14.2',
    'python-crontab==2.6.0'
]


dev_dependencies = {
    'dev': [
        'flake8==4.0.1',
        'isort>=4.2.15,<5.10.2',
        'bumpversion==0.6.0',
        'pytest==7.1.2',
        'pytest-cov==3.0.0',
        'twine==4.0.1',
        'mock==4.0.3',
        'freezegun==1.2.1'
    ]
}

setup(
    name='docker-lvmpy',
    version=find_version(),
    include_package_data=True,
    description='SKALE docker lvm2 volume plugin',
    long_description_markdown_filename='README.md',
    author='SKALE Labs',
    author_email='support@skalelabs.com',
    maintainer='SKALE Labs team',
    maintainer_email='support@skalelabs.com',
    url='https://github.com/skalenetwork/docker-lvmpy',
    install_requires=dependencies,
    extras_require=dev_dependencies,
    python_requires='>=3.7,<4',
    keywords=['skale', 'docker', 'lvmpy'],
    packages=find_packages(exclude=['tests']),
    entry_points={
        'console_scripts': {
          'lvmpy = docker_lvmpy.app:main'
        }
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.7',
    ],
)
