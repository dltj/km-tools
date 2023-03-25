"""Post to Twitter"""
import logging

import exceptions
from config import config
from source import Origin, Resource, WebResource
from TwitterAPI import TwitterAPI

from action import Action

logger = logging.getLogger(__name__)


class Twitter(Action):
    attributes_supplied = ["tweet_id"]
    action_table = "action_twitter"

    def __init__(self) -> None:
        super().__init__()

    def url_action(self, source: WebResource = None):
        """Tweet title and link to source.

        :param source: Instance of class WebResource

        :returns: None
        """
        twiter_api = TwitterAPI(
            config.settings.twitter.consumer_key,
            config.settings.twitter.consumer_secret,
            config.settings.twitter.access_token_key,
            config.settings.twitter.access_token_secret,
        )

        short_url_length = 23
        annotation_length = 0
        annotation_addition = ""
        if source.annotation_url:
            annotation_addition = " \U0001F5D2 annotated "
            annotation_length = len(annotation_addition) + short_url_length
            annotation_addition += source.annotation_url

        url_length = (
            short_url_length
            if len(source.normalized_url) > short_url_length
            else len(source.normalized_url)
        )
        meta_text = 4
        text_length = 280 - url_length - meta_text - annotation_length
        tweet_text = f"🔖 {source.title[:text_length]} {source.normalized_url}{annotation_addition}"

        if config.dry_run:
            logger.info(f"Would have tweeted: {tweet_text}")
            return ""  ## Dry-run, so return empty string

        r = twiter_api.request("statuses/update", {"status": tweet_text})
        if r.status_code == 200:
            logger.info(f"Successfully tweeted: '{tweet_text}'")
            tweet_id = r.json()["id_str"]
        else:
            logger.warning(f"Couldn't tweet ({r.status_code}): {r.text}")
            raise exceptions.TweetError(r.status_code, r.text)

        logger.info(f"Successfully tweeted {source.uri} as {tweet_id}")
        Action._save_attributes(self, source, self.attributes_supplied, [tweet_id])
        return tweet_id

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


twitter_action = Twitter()
config.actions.append(twitter_action)
