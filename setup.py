from setuptools import setup, find_packages
from ckanext.qa import __version__

setup(
    name='ckanext-qa',
    version=__version__,
    description='Quality Assurance plugin for CKAN',
    long_description='',
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ],
    keywords='',
    author='Open Knowledge Foundation, Cabinet Office & contributors',
    author_email='info@okfn.org',
    url='http://ckan.org/wiki/Extensions',
    license='mit',
    packages=find_packages(exclude=['tests']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    entry_points='''
    [paste.paster_command]
    qa=ckanext.qa.commands:QACommand

    [ckan.plugins]
    qa=ckanext.qa.plugin:QAPlugin

    [ckan.celery_task]
    tasks=ckanext.qa.celery_import:task_imports
    ''',
)
