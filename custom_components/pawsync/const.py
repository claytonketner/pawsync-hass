"""Constants for the Pawsync integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "pawsync"

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

NORMAL_POLL_INTERVAL = timedelta(minutes=15)
FAST_POLL_INTERVAL = timedelta(seconds=15)
FEED_FAST_POLL_DURATION = timedelta(minutes=5)
