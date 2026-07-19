import logging
from datetime import date

from sqlalchemy.orm import Session

from kmtools.models import ActionObsidianDaily, WebResource
from kmtools.obsidian.daily_page import ObsidianDailyPage
from kmtools.util.obsidian import title_to_page

from .task_base import TaskBase
from .web_resource_action_base import WebResourceActionBase

logger = logging.getLogger(__name__)


class SetupObsidianDaily(TaskBase):
    """Setup the Obsidian Daily page"""

    task_name = "ObsidianDailySetupTask"

    def run(self) -> None:
        date_filename = date.today().strftime("%Y-%m-%d") + ".md"
        logger.info(f"Generating preamble for {date_filename}")
        with ObsidianDailyPage(file_name=date_filename) as page:
            page.update_template_dates()


class AddToObsidianDaily(WebResourceActionBase):
    """Add resource to the Obsidian Daily page"""

    action_name = "ObsidianDailyAction"

    def process(self, session: Session, resource: WebResource) -> None:
        """Add resource to the Obsidian Daily page

        :param session: SQLAlchemy session
        :param resource: Instance of class WebResource

        :raises:
            - ActionException: when the attempt to post to Obsidian results in an error
        """

        date_filename = date.today().strftime("%Y-%m-%d") + ".md"
        with ObsidianDailyPage(file_name=date_filename) as page:
            readings = page.readings
            readings.append(
                f"{resource.__class__.__name__}Resource: [[{title_to_page(resource.headline)}]] ({resource.publisher})"
            )
            page.readings = readings

        obsidian_daily_action: ActionObsidianDaily = ActionObsidianDaily(
            resource_id=resource.id,
            daily_filename=page.filepath.as_posix(),
        )
        session.add(obsidian_daily_action)
        return
