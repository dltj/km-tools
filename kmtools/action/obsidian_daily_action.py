import logging
from datetime import date

from sqlalchemy.orm import Session

from kmtools.action.action_base import ActionBase
from kmtools.models import ActionObsidianDaily, WebResource
from kmtools.obsidian.daily_page import ObsidianDailyPage
from kmtools.util.config import config
from kmtools.util.obsidian import title_to_page

logger = logging.getLogger(__name__)


class AddToObsidianDaily(ActionBase):
    """Add resource to the Obsidian Daily page"""

    action_name = "ObsidianDailyAction"

    def process(self, session: Session, resource: WebResource) -> None:
        """Add resource to the Obsidian Daily page

        :param session: SQLAlchemy session
        :param resource: Instance of class WebResource

        :raises:
            - ActionException: when the attempt to post to Obsidian results in an error
        """

        if resource.__class__.__name__ == "HypothesisPage":
            return

        date_filename = date.today().strftime("%Y-%m-%d") + ".md"
        obsidian_daily_page = ObsidianDailyPage(file_name=date_filename)
        obsidian_daily_page.readings.append(
            f"{resource.__class__.__name__}Resource: [[{title_to_page(resource.headline)}]] ({resource.publisher})"
        )
        obsidian_daily_page.save()
        obsidian_daily_action: ActionObsidianDaily = ActionObsidianDaily(
            resource_id=resource.id,
            daily_filename=obsidian_daily_page.filepath.as_posix(),
        )
        session.add(obsidian_daily_action)
        return


def main():
    logger.setLevel(logging.DEBUG)
    config.dry_run = True

    actions = [
        AddToObsidianDaily(),
    ]

    for action in actions:
        action.run()


if __name__ == "__main__":
    main()
