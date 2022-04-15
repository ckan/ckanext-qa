# -*- coding: utf-8 -*-

import click
from ckanext.qa import utils


def get_commands():
    return [qa]


@click.group()
def qa():
    pass


@qa.command()
def init():
    """Creates necessary db tables"""
    utils.init_db()
