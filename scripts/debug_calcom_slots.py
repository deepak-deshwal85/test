import asyncio
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

load_dotenv(".env")


async def main() -> None:
    import httpx

    start = date.today().isoformat()
    end = (date.today() + timedelta(days=14)).isoformat()
    params = {
        "eventTypeId": "6073963",
        "start": start,
        "end": end,
        "timeZone": "Asia/Kolkata",
    }
    headers = {
        "cal-api-version": "2024-09-04",
        "Authorization": f"Bearer {os.getenv('CALCOM_API_KEY', '')}",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            "https://api.cal.com/v2/slots",
            params=params,
            headers=headers,
        )
        print("status:", response.status_code)
        print(json.dumps(response.json(), indent=2)[:4000])


if __name__ == "__main__":
    asyncio.run(main())
