#!/usr/bin/env python3
"""Build the small image and JSON payload served to the ESP32."""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"
QUOTES_PATH = ROOT / "quotes.txt"
IMAGES_DIR = ROOT / "images"
PUBLIC_DIR = ROOT / "public"
JSON_PATH = PUBLIC_DIR / "today.json"
JPEG_PATH = PUBLIC_DIR / "today.jpg"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def read_config() -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    required = ("latitude", "longitude", "timezone", "image_width", "image_height")
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Missing config key(s): {', '.join(missing)}")

    # Validate the timezone early so a typo is obvious in Actions.
    ZoneInfo(str(config["timezone"]))
    config["image_width"] = int(config["image_width"])
    config["image_height"] = int(config["image_height"])
    config["jpeg_quality"] = int(config.get("jpeg_quality", 85))
    if config["image_width"] <= 0 or config["image_height"] <= 0:
        raise ValueError("Image dimensions must be positive integers")
    return config


def day_number(local_date: date) -> int:
    return (local_date - date(2024, 1, 1)).days


def choose_quote(local_date: date) -> str:
    quotes = [
        line.strip()
        for line in QUOTES_PATH.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not quotes:
        return "Make today count."
    return quotes[day_number(local_date) % len(quotes)]


def image_files() -> list[Path]:
    IMAGES_DIR.mkdir(exist_ok=True)
    return sorted(
        (
            path
            for path in IMAGES_DIR.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ),
        key=lambda path: path.name.casefold(),
    )


def make_placeholder(size: tuple[int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, "#172136")
    draw = ImageDraw.Draw(image)
    for y in range(height):
        blend = y / max(height - 1, 1)
        color = (
            int(23 + 22 * blend),
            int(33 + 31 * blend),
            int(54 + 46 * blend),
        )
        draw.line((0, y, width, y), fill=color)

    font = ImageFont.load_default()
    message = "ADD A PHOTO TO /images"
    box = draw.textbbox((0, 0), message, font=font)
    text_width = box[2] - box[0]
    text_height = box[3] - box[1]
    draw.rounded_rectangle(
        (
            (width - text_width) // 2 - 10,
            (height - text_height) // 2 - 8,
            (width + text_width) // 2 + 10,
            (height + text_height) // 2 + 8,
        ),
        radius=8,
        fill="#ffffff",
    )
    draw.text(
        ((width - text_width) // 2, (height - text_height) // 2),
        message,
        fill="#172136",
        font=font,
    )
    return image


def build_image(local_date: date, config: dict[str, Any]) -> str | None:
    size = (config["image_width"], config["image_height"])
    candidates = image_files()
    selected = candidates[day_number(local_date) % len(candidates)] if candidates else None

    if selected:
        with Image.open(selected) as source:
            source = ImageOps.exif_transpose(source).convert("RGB")
            output = ImageOps.fit(source, size, method=Image.Resampling.LANCZOS)
    else:
        output = make_placeholder(size)

    # Baseline JPEG is deliberately used for broad ESP32 decoder compatibility.
    output.save(
        JPEG_PATH,
        format="JPEG",
        quality=config["jpeg_quality"],
        optimize=True,
        progressive=False,
        subsampling=2,
    )
    return selected.name if selected else None


def fetch_weather(config: dict[str, Any]) -> tuple[float, str, str]:
    params = urlencode(
        {
            "latitude": config["latitude"],
            "longitude": config["longitude"],
            "current": "temperature_2m",
            "daily": "sunset",
            "timezone": config["timezone"],
            "forecast_days": 1,
        }
    )
    request = Request(
        f"https://api.open-meteo.com/v1/forecast?{params}",
        headers={"User-Agent": "esp32-clock-github-actions/1.0"},
    )
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)

    temperature = round(float(payload["current"]["temperature_2m"]), 1)
    sunset_iso = str(payload["daily"]["sunset"][0])
    sunset = sunset_iso.rsplit("T", 1)[-1][:5]
    observed_at = str(payload["current"]["time"])
    return temperature, sunset, observed_at


def previous_weather() -> tuple[float | None, str | None, str | None]:
    if not JSON_PATH.exists():
        return None, None, None
    try:
        previous = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        return (
            previous.get("temperature_c"),
            previous.get("sunset"),
            previous.get("weather_observed_at"),
        )
    except (OSError, ValueError, TypeError):
        return None, None, None


def main() -> int:
    config = read_config()
    timezone = ZoneInfo(str(config["timezone"]))
    now = datetime.now(timezone)
    local_date = now.date()
    PUBLIC_DIR.mkdir(exist_ok=True)

    image_source = build_image(local_date, config)
    quote = choose_quote(local_date)
    weather_ok = True
    weather_error: str | None = None

    try:
        temperature, sunset, observed_at = fetch_weather(config)
    except Exception as exc:  # Keep Pages deployable during a temporary API outage.
        weather_ok = False
        weather_error = type(exc).__name__
        temperature, sunset, observed_at = previous_weather()
        print(
            f"Weather update failed; keeping the previous reading: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )

    output = {
        "date": local_date.isoformat(),
        "updated_at": now.isoformat(timespec="seconds"),
        "timezone": config["timezone"],
        "temperature_c": temperature,
        "sunset": sunset,
        "quote": quote,
        "image": "today.jpg",
        "image_source": image_source,
        "image_width": config["image_width"],
        "image_height": config["image_height"],
        "weather_observed_at": observed_at,
        "weather_ok": weather_ok,
    }
    if weather_error:
        output["weather_error"] = weather_error

    JSON_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Built {JPEG_PATH.relative_to(ROOT)} and {JSON_PATH.relative_to(ROOT)} "
        f"for {local_date.isoformat()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
