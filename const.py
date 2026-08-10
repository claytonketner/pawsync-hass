"""Constants for the Pawsync integration."""

from homeassistant.const import Platform

DOMAIN = "pawsync"
PAWSYNC_COORDINATOR = "pawsync_coordinator"

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH, Platform.NUMBER]

TOKEN_INVALID_CODE = -11008800  # Pawsync API code when auth token has expired

# How long (seconds) a feed service call keeps the coordinator on fast polling.
CONF_FEED_FAST_POLL_DURATION = "feed_fast_poll_duration"
DEFAULT_FEED_FAST_POLL_DURATION = 300
