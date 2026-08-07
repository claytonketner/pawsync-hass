from custom_components.pawsync.const import FAST_POLL_INTERVAL, NORMAL_POLL_INTERVAL


async def test_default_interval_is_normal(loaded_entry):
    coordinator = loaded_entry.runtime_data
    assert coordinator.update_interval == NORMAL_POLL_INTERVAL


async def test_request_fast_poll_switches_interval(loaded_entry):
    coordinator = loaded_entry.runtime_data

    coordinator.request_fast_poll()

    assert coordinator.update_interval == FAST_POLL_INTERVAL


async def test_fast_poll_reverts_after_duration(loaded_entry, freezer):
    coordinator = loaded_entry.runtime_data

    coordinator.request_fast_poll()
    assert coordinator.update_interval == FAST_POLL_INTERVAL

    freezer.tick(3600)  # well past FEED_FAST_POLL_DURATION
    coordinator._apply_polling_interval()

    assert coordinator.update_interval == NORMAL_POLL_INTERVAL


async def test_manual_fast_polling_keeps_interval_fast(loaded_entry):
    coordinator = loaded_entry.runtime_data

    coordinator.manual_fast_polling = True
    coordinator._apply_polling_interval()

    assert coordinator.update_interval == FAST_POLL_INTERVAL
