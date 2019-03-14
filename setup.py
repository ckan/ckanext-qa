from setuptools import setup, find_packages
from ckanext.qa import __version__

setup(
    name='ckanext-qa',
    version=__version__,
    description='Quality Assurance plugin for CKAN',
    long_description='',
    classifiers=[],
    keywords='',
    author='Open Knowledge Foundation, Cabinet Office & contributors',
    author_email='info@okfn.org',
    url='http://ckan.org/wiki/Extensions',
    license='mit',
    packages=find_packages(exclude=['tests']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'ckanext-archiver>=2.0',
        'ckanext-report',
        'SQLAlchemy>=0.6.6',
        'requests',
        'xlrd>=0.8.0',
        'messytables>=0.8',
        'python-magic>=0.4',
        'progressbar',
        'six>=1.9'  # until messytables->html5lib releases https://github.com/html5lib/html5lib-python/pull/301
    ],
    tests_require=[
        'nose',
        'mock',
        'flask'
    ],
    entry_points='''
    [paste.paster_command]
    qa=ckanext.qa.commands:QACommand

    [ckan.plugins]
    qa=ckanext.qa.plugin:QAPlugin

    [ckan.celery_task]
    tasks=ckanext.qa.celery_import:task_imports
    ''',
)
