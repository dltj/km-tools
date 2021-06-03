import collections

Source = collections.namedtuple(
    "Source",
    [
        "new_entries_handler",
        "save_entry_handler",
    ],
)
