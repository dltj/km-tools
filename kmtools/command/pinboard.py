import click

from ..source.pinboard import fetch


@click.group()
def pinboard():
    """Commands for Pinboard"""


@pinboard.command(name="fetch")
@click.pass_obj
def fetch_command(ctx_obj):
    """Retrieve annotations"""
    return fetch(ctx_obj)
