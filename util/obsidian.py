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
