"""Output links that have been robustified."""

import logging
from string import Template

import click

from kmtools.action import wayback_action
from kmtools.exceptions import MoreThanOneError, ResourceNotFoundError
from kmtools.models import WebResource

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--jekyll",
    "style",
    flag_value="jekyll",
    default=True,
    help="Output in Jekyll 'include html' format (default)",
)
@click.option(
    "--html",
    "style",
    flag_value="html",
    help="Output in HTML <a> anchor format",
)
@click.option(
    "--thursday-threads",
    "style",
    flag_value="tt",
    help="Output in Jekyll 'include thursday-threads' format",
)
@click.argument("url")
@click.pass_obj
def robustify(details, style, url):
    """Output markup for a robust link"""
    logger.debug(f"Searching for {url}")

    try:
        webpage: WebResource = wayback_action.find_entry(url)
    except MoreThanOneError:
        logger.error(f"More than one wayback entry found for {url}. Exiting.")
        return
    except ResourceNotFoundError:
        logger.error(f"{url} not found in wayback database. Exiting.")
        return

    # archive_date = webpage.saved_timestamp.isoformat()

    if style == "html":
        robust_template = Template(
            '<a href="$href" data-versionurl="$archive_url" '
            'data-versiondate="$archive_date" title="$title | $publisher">REPLACE_ME</a>'
        )
    elif style == "tt":
        robust_template = Template(
            """
{{ thursday_threads_quote(href="$href",
 blockquote='',
 versiondate="$archive_date",
 versionurl="$archive_url",
 anchor="$title",
 post=", $publisher") }}
"""
        )
    else:
        robust_template = Template(
            '{{ robustlink(href="$href", versionurl="$archive_url", versiondate="$archive_date", title="$title | $publisher", anchor="") }}'
        )

    robust_string = robust_template.substitute(
        {
            "href": webpage.href,
            "archive_url": webpage.action_wayback.wayback_url,
            "archive_date": webpage.action_wayback.processed_at,
            "title": webpage.headline,
            "publisher": webpage.publisher,
        }
    )

    print(robust_string)
