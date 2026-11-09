import os
import unittest
from unittest.mock import patch

import flip_broker


class FlipDiscoveryRetryTests(unittest.TestCase):
    def make_state(self):
        return {
            "tg_offset": 0,
            "last_discovery_date": None,
            "last_discovery_by_watch": {},
            "usage": {"month": None, "fetched": 0, "warned": False, "blocked": False},
            "seen": {},
            "deals": {},
        }

    def make_watches(self):
        return [
            {"id": "watch-a", "query": "camera", "city": "miami", "max_price": 500, "results_cap": 2},
            {"id": "watch-b", "query": "console", "city": "miami", "max_price": 500, "results_cap": 2},
        ]

    @patch.dict(os.environ, {"HUB_FETCH_URL": "https://example.invalid/watches"}, clear=False)
    @patch("flip_broker.http_json", return_value={"watches": []})
    def test_empty_hub_watch_list_requests_file_fallback(self, _http):
        self.assertIsNone(flip_broker.load_hub_watches())

    @patch("flip_broker.time.sleep")
    @patch("flip_broker.load_comps", return_value=[(100.0, "fixture")])
    @patch("flip_broker.apify_search", side_effect=[[], None, []])
    @patch("flip_broker.tg_send")
    def test_failed_watch_retries_without_rescanning_successful_watch(
        self, _send, apify, _comps, _sleep
    ):
        state = self.make_state()
        watches = self.make_watches()

        flip_broker.discovery(state, watches)
        self.assertEqual(state["last_discovery_by_watch"].get("watch-a"),
                         flip_broker.datetime.now(flip_broker.timezone.utc).strftime("%Y-%m-%d"))
        self.assertNotIn("watch-b", state["last_discovery_by_watch"])
        self.assertIsNone(state["last_discovery_date"])

        flip_broker.discovery(state, watches)
        self.assertEqual(apify.call_count, 3)
        self.assertEqual(apify.call_args_list[1].args[0]["id"], "watch-b")
        self.assertEqual(apify.call_args_list[2].args[0]["id"], "watch-b")
        self.assertEqual(
            len(state["last_discovery_by_watch"]), 2
        )
        self.assertEqual(
            state["last_discovery_date"],
            flip_broker.datetime.now(flip_broker.timezone.utc).strftime("%Y-%m-%d"),
        )


if __name__ == "__main__":
    unittest.main()
