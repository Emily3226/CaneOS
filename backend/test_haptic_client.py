"""
Mirrors test_client.py, but for the haptic reflex path: connects to
ws://localhost:8765/ws/haptics and prints each incoming direction message
with a local timestamp, so you can watch the (intentionally unthrottled)
haptic broadcasts fire in real time.

Usage:
    python test_haptic_client.py                       # ws://localhost:8765/ws/haptics
    python test_haptic_client.py ws://192.168.1.5:8765/ws/haptics
"""

import asyncio
import datetime
import json
import sys

import websockets

DEFAULT_URL = "ws://localhost:8765/ws/haptics"


async def main(url: str) -> None:
    print(f"Connecting to {url} ...")
    async with websockets.connect(url) as ws:
        print("Connected. Waiting for haptic messages (Ctrl+C to quit)...")
        async for raw_message in ws:
            message = json.loads(raw_message)
            timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] {message}")


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    try:
        asyncio.run(main(target_url))
    except KeyboardInterrupt:
        pass
