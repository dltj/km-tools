"""Post to Mastodon"""
import logging

import click
from mastodon import Mastodon as mastodon_library

from kmtools.action import Action
from kmtools.source import Origin, Resource, WebResource
from kmtools.util.config import config

logger = logging.getLogger(__name__)


class Mastodon(Action):
    attributes_supplied = ["toot_url"]
    action_table = "action_mastodon"

    def __init__(self) -> None:
        super().__init__()

    def url_action(self, source: WebResource = None):
        """Toot title and link to source.

        :param source: Instance of class WebResource

        :returns: None
        """
        mastodon_client = mastodon_library(
            client_id=config.settings.mastodon.client_id,
            client_secret=config.settings.mastodon.client_secret,
            access_token=config.settings.mastodon.access_token,
            api_base_url=config.settings.mastodon.api_base_url,
        )

        annotation_addition = ""
        if source.annotation_url:
            annotation_addition = f" \U0001F5D2 annotated {source.annotation_url}"

        url_length = len(source.normalized_url)
        annotation_length = len(annotation_addition)
        hashtag = " #BookmarkShare"
        meta_text = 4
        text_length = 500 - url_length - meta_text - annotation_length - len(hashtag)
        toot_text = f"🔖 {source.title[:text_length]} {source.normalized_url}{annotation_addition}{hashtag}"

        if config.dry_run:
            logger.info(f"Would have tooted: {toot_text}")
            return ""  ## Dry-run, so return empty string

        try:
            toot_dict = mastodon_client.toot(toot_text)
        except mastodon.MastodonError as err:
            logger.info(f"Couldn't toot: {err}")
            raise SystemExit from err
        logger.debug(f"Successfully tooted ({toot_dict['uri']}): '{toot_text}'")

        logger.info(f"Successfully tooted {source.uri} as {toot_dict['uri']}")
        Action._save_attributes(
            self, source, self.attributes_supplied, [toot_dict["uri"]]
        )
        return toot_dict["uri"]

    def attribute_read(self, source: Resource, name: str) -> str:
        return Action._attribute_read(self, name, self.action_table, source.uri)

    def process_new(self, origin: Origin) -> None:
        """Process entries that have not yet been processed by this action.

        :param origin: Instance of class Origin that we are processing

        :return: None
        """

        Action.process_new(
            self,
            action_table=self.action_table,
            origin=origin,
            url_action=self.url_action,
        )


mastodon_action = Mastodon()
config.actions.append(mastodon_action)


@click.group()
def mastodon():
    """Commands for Mastodon"""


@mastodon.command(name="toot")
@click.argument("url")
@click.argument("text")
def toot_command(url, text):
    """Retrieve annotations"""
    raise NotImplementedError("Haven't implemented tooting on command yet.")
