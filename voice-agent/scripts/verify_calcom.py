#!/usr/bin/env python3
"""Verify Cal.com credentials and event type configuration."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from calcom_client import CalComClient, CalComEventConfig
from client_config import load_client_config


async def main(phone_number: str) -> int:
    load_dotenv(".env.local")
    load_dotenv(".env")

    config = load_client_config(phone_number)
    if config.calcom is None:
        print("Cal.com is not configured for this phone number.")
        return 1

    client = CalComClient(api_key=os.getenv("CALCOM_API_KEY", "").strip() or None)
    calcom = config.calcom
    print(f"Client: {config.client_name}")
    print(f"Cal.com user: {calcom.username}")
    print(f"Event slug: {calcom.event_type_slug}")

    try:
        event_types = await client.fetch_event_types(calcom.username)
    except Exception as exc:
        print(f"Failed to list event types: {exc}")
        event_types = []

    if event_types:
        print("Available event types:")
        for event_type in event_types:
            marker = (
                " <-- configured" if event_type.slug == calcom.event_type_slug else ""
            )
            print(
                f"  - {event_type.slug} (id={event_type.event_type_id}, title={event_type.title}){marker}"
            )
    else:
        print("No event types returned. Check CALCOM_API_KEY and username.")

    event_config = CalComEventConfig(
        username=calcom.username,
        event_type_slug=calcom.event_type_slug,
        event_type_id=calcom.event_type_id,
        organization_slug=calcom.organization_slug,
    )
    start = date.today().isoformat()
    end = (date.today() + timedelta(days=7)).isoformat()
    try:
        slots = await client.fetch_available_slots(
            event_config,
            start_date=start,
            end_date=end,
            timezone=os.getenv("MEETING_TIMEZONE", "Asia/Kolkata"),
        )
        print(f"Slots found in next 7 days: {len(slots)}")
        for slot in slots[:5]:
            print(f"  - {slot.isoformat()}")
    except Exception as exc:
        print(f"Slot lookup failed: {exc}")
        print(
            "If the slug is wrong, update calcom_event_type_slug in the phone config "
            "or set calcom_event_type_id."
        )
        await client.aclose()
        return 1

    await client.aclose()
    print("Cal.com configuration looks good.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phone",
        default=os.getenv("CLIENT_PHONE_OVERRIDE", "911171366880"),
        help="Phone number config to verify",
    )
    raise SystemExit(
        asyncio.run(
            main("".join(ch for ch in parser.parse_args().phone if ch.isdigit()))
        )
    )
