"""Abstract base class for standalone Tasks"""

import logging
from abc import abstractmethod

logger = logging.getLogger(__name__)


class TaskBase:
    """Abstract base class for standalone tasks that don't operate on a resource queue.

    Subclasses must define:
        - task_name: str
        - run() -> None
    """

    task_name: str

    @abstractmethod
    def run(self) -> None:
        """Perform the task."""
        raise NotImplementedError
