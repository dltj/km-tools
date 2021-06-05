"""Post to Twitter"""
from TwitterAPI import TwitterAPI
from action import Action
import exceptions


def register_hourly_action():
    return Action("tweet_url", tweet_entry)


def tweet_entry(details, url=None, text=None, annotation_url=None):
    """Post to Twitter"""
    twiter_api = TwitterAPI(
        details.config.twitter.consumer_key,
        details.config.twitter.consumer_secret,
        details.config.twitter.access_token_key,
        details.config.twitter.access_token_secret,
    )

    # Get the number of characters a Twitter-shortened URL will take up
    if not details.twitter_short_url_length:
        r = twiter_api.request("help/configuration")
        twitter_config = r.json()
        details.twitter_short_url_length = twitter_config["short_url_length_https"]
    short_url_length = details.twitter_short_url_length

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
