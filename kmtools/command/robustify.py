"""Output links that have been robustified."""

import logging
from string import Template

import click

from kmtools.action.wayback_action import wayback_action
from kmtools.exceptions import MoreThanOneError, ResourceNotFoundError

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
        webpage = wayback_action.find_entry(url)
    except MoreThanOneError:
        logger.error(f"More than one wayback entry found for {url}. Exiting.")
        return
    except ResourceNotFoundError:
        logger.error(f"{url} not found in wayback database. Exiting.")
        return

    archive_date = webpage.timestamp.isoformat()

    if style == "html":
        robust_template = Template(
            '<a href="$href" data-versionurl="$archive_url" '
            'data-versiondate="$archive_date" title="$title">REPLACE_ME</a>'
        )
    elif style == "tt":
        robust_template = Template(
            """
{% include thursday-threads-quote.html
blockquote=''
href="$href"
versionurl="$archive_url"
versiondate="$archive_date"
anchor="$title"
post=''
%}"""
        )
    else:
        robust_template = Template(
            '{% include robustlink.html href="$href" versionurl="$archive_url" '
            'versiondate="$archive_date" title="$title" anchor="REPLACE_ME" %}',
        )

    robust_string = robust_template.substitute(
        {
            "href": webpage.url,
            "archive_url": webpage.wayback_url,
            "archive_date": archive_date,
            "title": "TITLE-PLACEHOLDER",
        }
    )

    print(robust_string)
