import collections

ActionTuple = collections.namedtuple(
    "Action",
    [
        "db_column",
        "action_handler",
    ],
)
