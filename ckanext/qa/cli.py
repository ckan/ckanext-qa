# -*- coding: utf-8 -*-

import sys
import click
import ckanext.qa.utils as utils


def get_commands():
    return [qa]


@click.group()
def qa():
    """
    QA analysis of CKAN resources

    Usage::

        ckan -c <path to CKAN config file> qa init
           - Creates the database tables that QA expects for storing
           results

        ckan -c <path to CKAN config file> qa [options] update [dataset/group name/id]
           - QA analysis on all resources in a given dataset, or on all
           datasets if no dataset given

        ckan -c <path to CKAN config file> qa sniff {filepath}
           - Opens the file and determines its type by the contents

        ckan -c <path to CKAN config file> qa view [dataset name/id]
           - See package score information

        ckan -c <path to CKAN config file> qa clean
           - Remove all package score information

        ckan -c <path to CKAN config file> qa migrate1
           - Migrates the way results are stored in task_status,
             with commit 6f63ab9e 20th March 2013
             (from key='openness_score'/'openness_score_failure_count' to
              key='status')

    The commands should be run from the ckanext-qa directory and expect
    a development.ini file to be present. Most of the time you will
    specify the config explicitly though::

        ckan -c <path to CKAN config file> qa update
    """


@qa.command()
def init():
    utils.init_db()


@qa.command()
@click.argument('ids', nargs=-1)
@click.option('-q', '--queue', help='Send to a particular queue')
def update(ids, queue):
    utils.update(ids, queue)


@qa.command()
@click.argument('filepaths', nargs=-1)
@click.option('-f', '--filepaths', help='Filepaths to sniff')
def sniff(filepaths):
    if len(filepaths) < 1:
        print('Not enough arguments', filepaths)
        sys.exit(1)

    utils.sniff(filepaths)


@qa.command()
@click.argument('package_ref')
def view(package_ref=None):
    utils.view(package_ref)


@qa.command()
def clean():
    utils.clean()


@qa.command()
def migrate1():
    utils.migrate1()
