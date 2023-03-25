"""Actions that are performed daily."""
import click
from action import obsidian_daily


@click.command()
@click.pass_obj
def daily(details):
    """Perform the daily activities"""
    obsidian_daily.daily(details)
