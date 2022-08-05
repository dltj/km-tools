""" Sources and actions to perform hourly """
import action
import click
from config import config
from source import hypothesis, pinboard


@click.command()
@click.pass_obj
def hourly(details):
    """Perform the hourly gathering from origins and action activations"""

    pinboard.fetch(details)
    hypothesis.fetch(details)

    action.wayback.wayback_action.update_jobs()

    for origin in config.origins:
        action.summarize.summarize_action.process_new(origin)
        action.twitter.twitter_action.process_new(origin)
        action.mastodon.mastodon_action.process_new(origin)
        action.wayback.wayback_action.process_new(origin)

    action.obsidian_hourly.obsidian_hourly_action.process_new(pinboard.pinboard_origin)
    action.obsidian_hourly.obsidian_hourly_action.process_new(
        hypothesis.hypothesis_annotation_origin
    )
