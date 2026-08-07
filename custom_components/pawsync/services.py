"""Entity services for the Pawsync integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.helpers import entity_platform

SERVICE_FEED = "feed"
ATTR_AMOUNT = "amount"

FEED_SERVICE_SCHEMA = {
    vol.Required(ATTR_AMOUNT): vol.All(vol.Coerce(int), vol.Range(min=1)),
}


def async_register_entity_services(platform: entity_platform.EntityPlatform) -> None:
    """Register Pawsync entity services on the given platform."""
    platform.async_register_entity_service(
        SERVICE_FEED, FEED_SERVICE_SCHEMA, "async_request_feed"
    )
