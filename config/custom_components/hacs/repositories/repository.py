"""Repository."""
# pylint: disable=broad-except, bad-continuation, no-member
import json
import os
import tempfile
import zipfile
from integrationhelper import Validate
from aiogithubapi import AIOGitHubAPIException
from .manifest import HacsManifest
from ..helpers.misc import get_repository_name
from ..handler.download import async_download_file, async_save_file
from ..helpers.install import version_to_install

from custom_components.hacs.repositories.helpers import RepositoryHelpers
from custom_components.hacs.hacsbase.exceptions import HacsException
from custom_components.hacs.store import async_remove_store
from custom_components.hacs.globals import get_hacs
from custom_components.hacs.helpers.information import (
    get_info_md_content,
    get_repository,
)
from custom_components.hacs.helpers.validate_repository import (
    common_validate,
    common_update_data,
)
from custom_components.hacs.repositories.repositorydata import RepositoryData


class RepositoryVersions:
    """Versions."""

    available = None
    available_commit = None
    installed = None
    installed_commit = None


class RepositoryStatus:
    """Repository status."""

    hide = False
    installed = False
    last_updated = None
    new = True
    selected_tag = None
    show_beta = False
    track = True
    updated_info = False
    first_install = True


class RepositoryInformation:
    """RepositoryInformation."""

    additional_info = None
    authors = []
    category = None
    default_branch = None
    description = ""
    state = None
    full_name = None
    file_name = None
    javascript_type = None
    homeassistant_version = None
    last_updated = None
    uid = None
    stars = 0
    info = None
    name = None
    topics = []


class RepositoryReleases:
    """RepositoyReleases."""

    last_release = None
    last_release_object = None
    last_release_object_downloads = None
    published_tags = []
    objects = []
    releases = False
    downloads = None


class RepositoryPath:
    """RepositoryPath."""

    local = None
    remote = None


class RepositoryContent:
    """RepositoryContent."""

    path = None
    files = []
    objects = []
    single = False


class HacsRepository(RepositoryHelpers):
    """HacsRepository."""

    def __init__(self):
        """Set up HacsRepository."""
        self.hacs = get_hacs()
        self.data = RepositoryData()
        self.content = RepositoryContent()
        self.content.path = RepositoryPath()
        self.information = RepositoryInformation()
        self.repository_object = None
        self.status = RepositoryStatus()
        self.state = None
        self.force_branch = False
        self.integration_manifest = {}
        self.repository_manifest = HacsManifest.from_dict({})
        self.validate = Validate()
        self.releases = RepositoryReleases()
        self.versions = RepositoryVersions()
        self.pending_restart = False
        self.tree = []
        self.treefiles = []
        self.ref = None

    @property
    def display_name(self):
        """Return display name."""
        return get_repository_name(self)

    @property
    def display_status(self):
        """Return display_status."""
        if self.data.new:
            return "new"
        elif self.pending_restart:
            return "pending-restart"
        elif self.pending_upgrade:
            return "pending-upgrade"
        elif self.data.installed:
            return "installed"
        else:
            return "default"

    @property
    def display_status_description(self):
        """Return display_status_description."""
        description = {
            "default": "Not installed.",
            "pending-restart": "Restart pending.",
            "pending-upgrade": "Upgrade pending.",
            "installed": "No action required.",
            "new": "This is a newly added repository.",
        }
        return description[self.display_status]

    @property
    def display_installed_version(self):
        """Return display_authors"""
        if self.data.installed_version is not None:
            return self.data.installed_version
        else:
            return (
                self.data.installed_commit
                if self.data.installed_commit is not None
                else ""
            )

    @property
    def display_available_version(self):
        """Return display_authors"""
        if self.data.last_version is not None:
            return self.data.last_version
        else:
            return self.data.last_commit if self.data.last_commit is not None else ""

    @property
    def display_version_or_commit(self):
        """Does the repositoriy use releases or commits?"""
        return "version" if self.data.releases else "commit"

    @property
    def main_action(self):
        """Return the main action."""
        actions = {
            "new": "INSTALL",
            "default": "INSTALL",
            "installed": "REINSTALL",
            "pending-restart": "REINSTALL",
            "pending-upgrade": "UPGRADE",
        }
        return actions[self.display_status]

    async def common_validate(self, ignore_issues=False):
        """Common validation steps of the repository."""
        await common_validate(self, ignore_issues)

    async def common_registration(self):
        """Common registration steps of the repository."""
        # Attach repository
        if self.repository_object is None:
            self.repository_object = await get_repository(
                self.hacs.session, self.hacs.configuration.token, self.data.full_name
            )
            self.data.update_data(self.repository_object.attributes)

        # Set topics
        self.data.topics = self.data.topics

        # Set stargazers_count
        self.data.stargazers_count = self.data.stargazers_count

        # Set description
        self.data.description = self.data.description

        if self.hacs.action and (
            self.data.description is None or len(self.data.description) == 0
        ):
            raise HacsException("Missing repository description")

    async def common_update(self, ignore_issues=False):
        """Common information update steps of the repository."""
        self.logger.debug("Getting repository information")

        # Attach repository
        await common_update_data(self, ignore_issues)

        # Update last updaeted
        self.data.last_updated = self.repository_object.attributes.get("pushed_at", 0)

        # Update last available commit
        await self.repository_object.set_last_commit()
        self.data.last_commit = self.repository_object.last_commit

        # Get the content of hacs.json
        await self.get_repository_manifest_content()

        # Update "info.md"
        self.information.additional_info = await get_info_md_content(self)

    async def download_zip(self, validate):
        """Download ZIP archive from repository release."""
        try:
            contents = False

            for release in self.releases.objects:
                self.logger.info(f"ref: {self.ref}  ---  tag: {release.tag_name}")
                if release.tag_name == self.ref.split("/")[1]:
                    contents = release.assets

            if not contents:
                return validate

            for content in contents or []:
                filecontent = await async_download_file(content.download_url)

                if filecontent is None:
                    validate.errors.append(f"[{content.name}] was not downloaded.")
                    continue

                result = await async_save_file(
                    f"{tempfile.gettempdir()}/{self.data.filename}", filecontent
                )
                with zipfile.ZipFile(
                    f"{tempfile.gettempdir()}/{self.data.filename}", "r"
                ) as zip_file:
                    zip_file.extractall(self.content.path.local)

                if result:
                    self.logger.info(f"download of {content.name} complete")
                    continue
                validate.errors.append(f"[{content.name}] was not downloaded.")
        except Exception:
            validate.errors.append("Download was not complete.")

        return validate

    async def download_content(self, validate, directory_path, local_directory, ref):
        """Download the content of a directory."""
        from custom_components.hacs.helpers.download import download_content

        validate = await download_content(self)
        return validate

    async def get_repository_manifest_content(self):
        """Get the content of the hacs.json file."""
        if "hacs.json" not in [x.filename for x in self.tree]:
            if self.hacs.action:
                raise HacsException("No hacs.json file in the root of the repository.")
            return
        if self.hacs.action:
            self.logger.info("Found hacs.json")

        self.ref = version_to_install(self)

        try:
            manifest = await self.repository_object.get_contents("hacs.json", self.ref)
            self.repository_manifest = HacsManifest.from_dict(
                json.loads(manifest.content)
            )
            self.data.update_data(json.loads(manifest.content))
            if self.hacs.action:
                self.logger.info(json.loads(manifest.content))
        except (AIOGitHubAPIException, Exception) as exception:  # Gotta Catch 'Em All
            if self.hacs.action:
                raise HacsException(f"hacs.json file is not valid ({exception}).")
        if self.hacs.action:
            self.logger.info("hacs.json is valid")

    def remove(self):
        """Run remove tasks."""
        self.logger.info("Starting removal")

        if self.data.id in self.hacs.common.installed:
            self.hacs.common.installed.remove(self.data.id)
        for repository in self.hacs.repositories:
            if repository.data.id == self.data.id:
                self.hacs.repositories.remove(repository)

    async def uninstall(self):
        """Run uninstall tasks."""
        self.logger.info("Uninstalling")
        if not await self.remove_local_directory():
            raise HacsException("Could not uninstall")
        self.data.installed = False
        if self.data.category == "integration":
            if self.data.config_flow:
                await self.reload_custom_components()
            else:
                self.pending_restart = True
        elif self.data.category == "theme":
            try:
                await self.hacs.hass.services.async_call(
                    "frontend", "reload_themes", {}
                )
            except Exception:  # pylint: disable=broad-except
                pass
        if self.data.full_name in self.hacs.common.installed:
            self.hacs.common.installed.remove(self.data.full_name)

        await async_remove_store(self.hacs.hass, f"hacs/{self.data.id}.hacs")

        self.data.installed_version = None
        self.data.installed_commit = None
        self.hacs.hass.bus.async_fire(
            "hacs/repository",
            {"id": 1337, "action": "uninstall", "repository": self.data.full_name},
        )

    async def remove_local_directory(self):
        """Check the local directory."""
        import shutil
        from asyncio import sleep

        try:
            if self.data.category == "python_script":
                local_path = f"{self.content.path.local}/{self.data.name}.py"
            elif self.data.category == "theme":
                if os.path.exists(
                    f"{self.hacs.system.config_path}/{self.hacs.configuration.theme_path}/{self.data.name}.yaml"
                ):
                    os.remove(
                        f"{self.hacs.system.config_path}/{self.hacs.configuration.theme_path}/{self.data.name}.yaml"
                    )
                local_path = self.content.path.local
            elif self.data.category == "integration":
                if not self.data.domain:
                    self.logger.error("Missing domain")
                    return False
                local_path = self.content.path.local
            else:
                local_path = self.content.path.local

            if os.path.exists(local_path):
                self.logger.debug(f"Removing {local_path}")

                if self.data.category in ["python_script"]:
                    os.remove(local_path)
                else:
                    shutil.rmtree(local_path)

                while os.path.exists(local_path):
                    await sleep(1)

        except Exception as exception:
            self.logger.debug(f"Removing {local_path} failed with {exception}")
            return False
        return True
