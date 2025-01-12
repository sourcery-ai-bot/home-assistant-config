"""Class for python_scripts in HACS."""
from custom_components.hacs.helpers.classes.exceptions import HacsException
from custom_components.hacs.helpers.classes.repository import HacsRepository
from custom_components.hacs.helpers.functions.information import find_file_name
from custom_components.hacs.helpers.functions.logger import getLogger


class HacsPythonScript(HacsRepository):
    """python_scripts in HACS."""

    category = "python_script"

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.data.full_name = full_name
        self.data.full_name_lower = full_name.lower()
        self.data.category = "python_script"
        self.content.path.remote = "python_scripts"
        self.content.path.local = self.localpath
        self.content.single = True
        self.logger = getLogger(f"repository.{self.data.category}.{full_name}")

    @property
    def localpath(self):
        """Return localpath."""
        return f"{self.hacs.system.config_path}/python_scripts"

    async def validate_repository(self):
        """Validate."""
        # Run common validation steps.
        await self.common_validate()

        # Custom step 1: Validate content.
        if self.data.content_in_root:
            self.content.path.remote = ""

        compliant = any(
            treefile.startswith(f"{self.content.path.remote}")
            and treefile.endswith(".py")
            for treefile in self.treefiles
        )
        if not compliant:
            raise HacsException(
                f"Repository structure for {self.ref.replace('tags/','')} is not compliant"
            )

        # Handle potential errors
        if self.validate.errors:
            for error in self.validate.errors:
                if not self.hacs.system.status.startup:
                    self.logger.error(error)
        return self.validate.success

    async def async_post_registration(self):
        """Registration."""
        # Set name
        find_file_name(self)

    async def update_repository(self, ignore_issues=False):
        """Update."""
        await self.common_update(ignore_issues)

        # Get python_script objects.
        if self.data.content_in_root:
            self.content.path.remote = ""

        compliant = any(
            treefile.startswith(f"{self.content.path.remote}")
            and treefile.endswith(".py")
            for treefile in self.treefiles
        )
        if not compliant:
            raise HacsException(
                f"Repository structure for {self.ref.replace('tags/','')} is not compliant"
            )

        # Update name
        find_file_name(self)
