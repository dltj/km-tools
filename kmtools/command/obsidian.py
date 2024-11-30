import click

from kmtools.action.obsidian_daily_action import AddToObsidianDaily


@click.group()
def obsidian():
    """Commands for local Obsidian database"""


@obsidian.command(name="daily")
@click.pass_obj
def daily_command(_):
    """Make daily Obsidian diary page"""
    return AddToObsidianDaily().run()
