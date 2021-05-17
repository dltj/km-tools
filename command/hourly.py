""" Sources and actions to perform hourly """
import click
from action.Twitter import twitter
from source.Pinboard import pinboard


@click.command()
@click.pass_obj
def hourly(details):
    """Perform the hourly gathering from sources and action activations"""
    pinboard(details)
    twitter(details)
