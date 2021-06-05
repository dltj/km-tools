import collections

Action = collections.namedtuple(
    "Action",
    [
        "db_column",
        "action_handler",
    ],
)
