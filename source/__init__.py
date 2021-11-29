import collections

Source = collections.namedtuple(
    "Source",
    [
        "new_entries_handler",
        "save_entry_handler",
    ],
)

Webpage = collections.namedtuple(
    "Webpage",
    [
        "ident",
        "href",
        "title",
        "description",
        "tags",
        "annotation_href",
        "archive_url",
        "archive_date",
    ],
)

Annotation = collections.namedtuple(
    "Annotation",
    [
        "id",
        "uri",
        "annotation",
        "created",
        "updated",
        "quote",
        "tags",
        "document_title",
        "link_html",
        "link_incontext",
        "hidden",
        "flagged",
    ],
)
