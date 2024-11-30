"""Utility functions for the Obsidian app"""


def get_link_for_file(file, link_text=""):
    """Create wiki-link syntax for a specific file name.

    :param file: file name to point to
    :param link_text: anchor text for the link

    :returns: Wiki-link syntax string
    """
    if link_text != "":
        return "[[" + file.replace(".md", "") + "|" + link_text + "]]"
    else:
        return "[[" + file.replace(".md", "") + "]]"


def title_to_page(title: str) -> str:
    """
    Transforms a source title into a valid Obsidian page name.

    This function takes a given title string and converts it into a format suitable
    for use as an Obsidian vault file name. It trims whitespace, replaces certain invalid
    characters with permissible substitutes, and ensures the resulting name does not
    exceed a typical filesystem limit by truncating it to 250 characters.

    Args:
        title (str): The original title to be transformed into a page name.

    Returns:
        str: A sanitized and truncated string suitable as an Obsidian page name.

    Notes:
        - ':' characters are replaced by '—' (em dash).
        - '/' characters are replaced by '-' (hyphen) to prevent directory issues.
        - Page names are limited to 250 characters to comply with common filesystem constraints.

    Example:
        >>> title_to_page("Project: Overview/Final Results")
        'Project— Overview-Final Results'
    """
    filename = title.strip().replace(":", "—").replace("/", "-")[:250]
    return filename
