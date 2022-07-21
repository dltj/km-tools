import click
<<<<<<< HEAD
from action import obsidian_daily
=======

from action import Action, obsidian_daily


class ObsidianAction(Action):
    attributes_supplied = ["obsidian_filename"]

    def __init__(self, url, obsidian_filename=None) -> None:
        super().__init__(url)
        self.obsidian_filename = obsidian_filename

    # @property
    # def obsidian_filename(self):
    #     if not self.obsidian_filename:

    #     return self.obsidian_filename

    # ## If overriding the default filename scheme
    # @obsidian_filename.setter
    # def obsidian_filename(self, value):
    #     self.obsidian_filename = value
>>>>>>> 49369e6d9efd671fbd7e07f55242012533099c5f


@click.group()
def obsidian():
    """Commands for local Obsidian database"""


@obsidian.command(name="daily")
@click.pass_obj
def daily_command(details):
    """Make daily Obsidian diary page"""
    return obsidian_daily.daily(details)
