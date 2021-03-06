"""Post to Twitter"""
import exceptions
from TwitterAPI import TwitterAPI

from action import ActionTuple


def register_hourly_action():
    return ActionTuple("tweet_url", tweet_entry)


def tweet_entry(details, url=None, text=None, annotation_url=None):
    """Post to Twitter"""
    twiter_api = TwitterAPI(
        details.settings.twitter.consumer_key,
        details.settings.twitter.consumer_secret,
        details.settings.twitter.access_token_key,
        details.settings.twitter.access_token_secret,
    )

    short_url_length = 23
    annotation_length = 0
    annotation_addition = ""
    if annotation_url:
        annotation_addition = " \U0001F5D2 annotated "
        annotation_length = len(annotation_addition) + short_url_length
        annotation_addition += annotation_url

    url_length = short_url_length if len(url) > short_url_length else len(url)
    meta_text = 4
    text_length = 280 - url_length - meta_text - annotation_length
    tweet_text = f"🔖 {text[:text_length]} {url}{annotation_addition}"
    if not details.dry_run:
        r = twiter_api.request("statuses/update", {"status": tweet_text})
        if r.status_code == 200:
            details.logger.debug(f"Successfully tweeted: '{tweet_text}'")
            tweet_id = r.json()["id_str"]
            return tweet_id
        else:
            details.logger.info(f"Couldn't tweet ({r.status_code}): {r.text}")
            raise exceptions.TweetError(r.status_code, r.text)
    else:
        details.logger.info(f"Would have tweeted: {tweet_text}")
        return ""  ## Dry-run, so return empty string
