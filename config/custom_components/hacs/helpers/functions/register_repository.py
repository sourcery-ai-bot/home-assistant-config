"""Register a repository."""
from aiogithubapi import AIOGitHubAPIException

from custom_components.hacs.helpers.classes.exceptions import (
    HacsException,
    HacsExpectedException,
)
from custom_components.hacs.share import get_hacs


# @concurrent(15, 5)
async def register_repository(full_name, category, check=True, ref=None):
    """Register a repository."""
    hacs = get_hacs()
    from custom_components.hacs.repositories import (
        RERPOSITORY_CLASSES,
    )  # To handle import error

    if full_name in hacs.common.skip and full_name != "hacs/integration":
        raise HacsExpectedException(f"Skipping {full_name}")

    if category not in RERPOSITORY_CLASSES:
        raise HacsException(f"{category} is not a valid repository category.")

    repository = RERPOSITORY_CLASSES[category](full_name)
    if check:
        try:
            await repository.async_registration(ref)
            if hacs.system.status.new:
                repository.data.new = False
            if repository.validate.errors:
                hacs.common.skip.append(repository.data.full_name)
                if not hacs.system.status.startup:
                    hacs.logger.error(f"Validation for {full_name} failed.")
                if hacs.action:
                    raise HacsException(f"::error:: Validation for {full_name} failed.")
                return repository.validate.errors
            if hacs.action:
                repository.logger.info("Validation completed")
            else:
                repository.logger.info("Registration completed")
        except AIOGitHubAPIException as exception:
            hacs.common.skip.append(repository.data.full_name)
            raise HacsException(f"Validation for {full_name} failed with {exception}.")

    exists = (
        False
        if str(repository.data.id) == "0"
        else [x for x in hacs.repositories if str(x.data.id) == str(repository.data.id)]
    )

    if exists:
        if exists[0] in hacs.repositories:
            hacs.repositories.remove(exists[0])

    elif hacs.hass is not None and (
            (check and repository.data.new) or hacs.system.status.new
        ):
        hacs.hass.bus.async_fire(
            "hacs/repository",
            {
                "id": 1337,
                "action": "registration",
                "repository": repository.data.full_name,
                "repository_id": repository.data.id,
            },
        )
    hacs.repositories.append(repository)
