import json
import unittest
from io import BytesIO
from unittest.mock import patch

import update


class FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class UpdateTests(unittest.TestCase):
    def test_open_meteo_payload_is_reduced_for_esp32(self):
        api_payload = {
            "current": {
                "temperature_2m": 31.24,
                "time": "2026-09-11T14:00",
            },
            "daily": {"sunset": ["2026-09-11T18:03"]},
        }

        def fake_urlopen(*_args, **_kwargs):
            return FakeResponse(json.dumps(api_payload).encode("utf-8"))

        with patch.object(update, "urlopen", fake_urlopen):
            result = update.fetch_weather(update.read_config())

        self.assertEqual(result, (31.2, "18:03", "2026-09-11T14:00"))


if __name__ == "__main__":
    unittest.main()
