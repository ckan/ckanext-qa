# -*- coding: utf-8 -*-

import click
import logging
import ckanext.qa.utils as utils


log = logging.getLogger(__name__)


def get_commands():
    return [qa]


@click.group()
def qa():
    pass


@qa.command()
def init():
    """Creates necessary db tables"""
    utils.init_db()


@qa.command()
@click.argument('ids', nargs=-1)
@click.option('-q', '--queue', default=None)
def update(ids, queue):
    """Creates necessary db tables"""
    log.info('QA update: ids:%s queue:%s' % (ids, queue))
    if ids:
        utils.update(*ids, queue=queue)
    else:
        utils.update(queue=queue)
