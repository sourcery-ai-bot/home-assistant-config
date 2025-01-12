"""API Handler for hacs_removed"""
import voluptuous as vol
from homeassistant.components import websocket_api

from custom_components.hacs.share import list_removed_repositories


@websocket_api.async_response
@websocket_api.websocket_command({vol.Required("type"): "hacs/removed"})
async def hacs_removed(hass, connection, msg):
    """Get information about removed repositories."""
    content = [repo.to_json() for repo in list_removed_repositories()]
    connection.send_message(websocket_api.result_message(msg["id"], content))
