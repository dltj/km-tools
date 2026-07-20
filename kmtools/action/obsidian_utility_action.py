import logging
from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from kmtools.obsidian.daily_page import ObsidianDailyPage

from .task_base import TaskBase

logger = logging.getLogger(__name__)


class ObsidianPageCleanup(TaskBase):
    """Remove unused elements of a daily notes page"""

    task_name = "ObsidianPageCleanupTask"
    _page_date = None

    def __init__(self, page_date: str | None = None) -> None:
        if page_date:
            self._page_date = page_date
        super().__init__()

    def run(self) -> None:
        if self._page_date:
            try:
                offset_dateobj: date = datetime.strptime(
                    self._page_date, "%Y-%m-%d"
                ).date()
            except ValueError:
                raise ValueError(
                    f"`{self._page_date}` is not a parsable YYYY-MM-DD date."
                )
        else:
            offset_dateobj = datetime.now() + relativedelta(days=-6)
        offset_date_filename = offset_dateobj.strftime("%Y-%m-%d") + ".md"

        logger.info(f"Generating preamble for {offset_date_filename}")
        with ObsidianDailyPage(file_name=offset_date_filename) as page:
            page.cleanup_empty_sections()
