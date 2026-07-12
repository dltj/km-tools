import logging

from mastodon import Mastodon as mastodon_library
from mastodon import errors as mastodon_errors
from sqlalchemy.orm import Session

from kmtools.exceptions import ActionError
from kmtools.models import ActionMastodon, WebResource
from kmtools.util.config import get_config

from .web_resource_action_base import WebResourceActionBase

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class PostToMastodonAction(WebResourceActionBase):
    """Post a resource to Mastodon"""

    action_name = "MastodonAction"

    @staticmethod
    def _toot_resource(resource: WebResource) -> str:
        """Toot title and link to source.

        :param resource:  WebResource object

        :returns: URI of the toot
        """
        config = get_config()
        mastodon_client = mastodon_library(
            client_id=config.mastodon.client_id,
            client_secret=config.mastodon.client_secret.get_secret_value(),
            access_token=config.mastodon.access_token.get_secret_value(),
            api_base_url=config.mastodon.api_base_url,
        )

        annotation_addition = ""
        if hasattr(resource, "annotations"):
            annotation_addition = f" \U0001f5d2 annotated {resource.annotation_url}"

        url_length = len(resource.normalized_url)
        annotation_length = len(annotation_addition)
        hashtag = " #BookmarkShare"
        meta_text = 4
        text_length = 500 - url_length - meta_text - annotation_length - len(hashtag)
        toot_text = f"🔖 {resource.title[:text_length]} {resource.normalized_url}{annotation_addition}{hashtag}"

        if config.dry_run:
            logger.info("Would have tooted: %s", toot_text)
            return ""  ## Dry-run, so return empty string

        try:
            toot_dict = mastodon_client.toot(toot_text)
        except mastodon_errors.MastodonError as err:
            logger.info("Couldn't toot: %s", err)
            raise mastodon_errors.MastodonError from err
        logger.info(
            "Successfully tooted %s as %s with %s",
            resource.url,
            toot_dict["uri"],
            toot_text,
        )
        return toot_dict["uri"]

    def process(self, session: Session, resource: WebResource) -> None:
        """Post a resource to Mastodon

        :param session: SQLAlchemy session
        :param resource: Instance of class WebResource

        :raises:
            - ActionException: when the attempt to post to Mastodon results in an error
        """

        mastodon_action: ActionMastodon = ActionMastodon(resource=resource)
        session.add(mastodon_action)
        try:
            toot_uri = PostToMastodonAction._toot_resource(resource)
        except mastodon_errors.MastodonError as e:
            raise ActionError("Mastodon error") from e

        mastodon_action.toot_uri = toot_uri
        # Note: Not committing the session here because the process_status object nees a status
        return


def main():
    # database.Base.metadata.create_all(database.engine)
    # with Session(database.engine) as session:
    #     pinb: Pinboard = Pinboard(
    #         hash="hashblah", href="hrefbalh", time="tieblah", shared=1, toread=1
    #     )
    #     session.add(pinb)
    #     session.commit()

    actions = [
        PostToMastodonAction(),
        # SaveToWaybackAction(),
        # PostToMastodonAction(),
    ]

    for action in actions:
        action.run()


if __name__ == "__main__":
    main()
