"""Post to Twitter"""
from TwitterAPI import TwitterAPI
import exceptions


def twitter(details, text=None, url=None):
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

    url_length = short_url_length if len(url) > short_url_length else len(url)
    meta_text = 4
    text_length = 280 - url_length - meta_text
    tweet_text = f"🔖 {text[:text_length]} {url}"
    if not details.dry_run:
        r = twiter_api.request("statuses/update", {"status": tweet_text})
        if r.status_code == 200:
            details.logger.debug(f"Successfully tweeted: '{tweet_text}'")
        else:
            details.logger.info(f"Couldn't tweet ({r.status_code}): {r.text}")
            raise exceptions.TweetError(r.status_code, r.text)
    else:
        details.logger.info(f"Would have tweeted: {tweet_text}")
