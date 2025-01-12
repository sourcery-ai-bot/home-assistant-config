"""Class for netdaemon apps in HACS."""
from custom_components.hacs.helpers.classes.exceptions import HacsException
from custom_components.hacs.helpers.classes.repository import HacsRepository
from custom_components.hacs.helpers.functions.filters import (
    get_first_directory_in_directory,
)
from custom_components.hacs.helpers.functions.logger import getLogger


class HacsNetdaemon(HacsRepository):
    """Netdaemon apps in HACS."""

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.data.full_name = full_name
        self.data.full_name_lower = full_name.lower()
        self.data.category = "netdaemon"
        self.content.path.local = self.localpath
        self.content.path.remote = "apps"
        self.logger = getLogger(f"repository.{self.data.category}.{full_name}")

    @property
    def localpath(self):
        """Return localpath."""
        return f"{self.hacs.system.config_path}/netdaemon/apps/{self.data.name}"

    async def validate_repository(self):
        """Validate."""
        await self.common_validate()

        # Custom step 1: Validate content.
        if self.repository_manifest and self.data.content_in_root:
            self.content.path.remote = ""

        if self.content.path.remote == "apps":
            self.data.domain = get_first_directory_in_directory(
                self.tree, self.content.path.remote
            )
            self.content.path.remote = f"apps/{self.data.name}"

        compliant = any(
            treefile.startswith(f"{self.content.path.remote}")
            and treefile.endswith(".cs")
            for treefile in self.treefiles
        )
        if not compliant:
            raise HacsException(
                f"Repostitory structure for {self.ref.replace('tags/','')} is not compliant"
            )

        # Handle potential errors
        if self.validate.errors:
            for error in self.validate.errors:
                if not self.hacs.system.status.startup:
                    self.logger.error(error)
        return self.validate.success

    async def update_repository(self, ignore_issues=False):
        """Update."""
        await self.common_update(ignore_issues)

        # Get appdaemon objects.
        if self.repository_manifest and self.data.content_in_root:
            self.content.path.remote = ""

        if self.content.path.remote == "apps":
            self.data.domain = get_first_directory_in_directory(
                self.tree, self.content.path.remote
            )
            self.content.path.remote = f"apps/{self.data.name}"

        # Set local path
        self.content.path.local = self.localpath

    async def async_post_installation(self):
        """Run post installation steps."""
        try:
            await self.hacs.hass.services.async_call(
                "hassio", "addon_restart", {"addon": "c6a2317c_netdaemon"}
            )
        except BaseException:
            pass
