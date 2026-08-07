#!/usr/bin/env python3
"""Command-line helper for exercising the Pawsync API directly."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.pawsync.api import PawsyncClient

_LOGGER = logging.getLogger(__name__)


async def _async_main(args: argparse.Namespace) -> None:
    async with aiohttp.ClientSession() as session:
        client = PawsyncClient(session, args.email, args.password)
        await client.async_login()

        devices = await client.async_get_device_list()
        for device in devices:
            print(device)

        if args.feed:
            await client.async_request_feed(devices[0], args.amount)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser("pawsync")
    parser.add_argument("email", type=str)
    parser.add_argument("password", type=str)
    parser.add_argument("--feed", action="store_true")
    parser.add_argument("--amount", type=int, default=12)
    asyncio.run(_async_main(parser.parse_args()))


if __name__ == "__main__":
    main()
