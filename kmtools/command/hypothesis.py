import click

from ..source.hypothesis import fetch


@click.group()
def hypothesis():
    """Commands for Hypothes.is"""


@hypothesis.command(name="fetch")
@click.pass_obj
def fetch_command(details):
    """Retrieve annotations"""
    return fetch(details)
