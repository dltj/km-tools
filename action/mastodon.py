"""Post to Mastodon"""
import click

from action import ActionTuple
from mastodon import Mastodon


@click.group()
def mastodon():
    """Commands for Mastodon"""


@mastodon.command(name="toot")
@click.argument("url")
@click.argument("text")
@click.pass_obj
def fetch_command(details, url, text):
    """Retrieve annotations"""
    toot_uri = toot_entry(details, url=url, text=text, annotation_url=None)
    print(f"{toot_uri=}")
    return toot_uri


# def register_source():
#     return Source(new_entries, save_entry)
#
#
# def fetch(details):
#     """Update local Hypothesis database"""


def register_hourly_action():
    return ActionTuple("toot_url", toot_entry)


def toot_entry(details, url=None, text=None, annotation_url=None):
    """Post to Mastodon"""
    mastodon_client = Mastodon(
        client_id=details.settings.mastodon.client_id,
        client_secret=details.settings.mastodon.client_secret,
        access_token=details.settings.mastodon.access_token,
        api_base_url=details.settings.mastodon.api_base_url,
    )

    annotation_length = 0
    annotation_addition = ""
    if annotation_url:
        annotation_addition = f" \U0001F5D2 annotated {annotation_url}"

    url_length = len(url)
    meta_text = 4
    text_length = 500 - url_length - meta_text - annotation_length
    toot_text = f"🔖 {text[:text_length]} {url}{annotation_addition}"
    if not details.dry_run:
        try:
            toot_dict = mastodon_client.toot(toot_text)
        except mastodon.MastodonError as err:
            details.logger.info(f"Couldn't toot: {err}")
            raise SystemExit from err
        details.logger.debug(f"Successfully tooted ({toot_dict['uri']}): '{toot_text}'")
        return toot_dict["uri"]
    else:
        details.logger.info(f"Would have tooted: {toot_text}")
        return ""  ## Dry-run, so return empty string
