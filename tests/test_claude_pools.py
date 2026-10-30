import unittest

import support
from model_routing.adapters import ClaudeAdapter, unknown_usage
from model_routing.catalog import load_catalog
from model_routing.choose import choose
from model_routing.settings import load_yaml, merge_layers, normalize

CLAUDE = ClaudeAdapter()


def settings_with(**routing):
    base = load_yaml(support.ROOT / "data" / "prefs-defaults.yaml")
    return normalize(merge_layers(base, {"routing": routing}))


def reports():
    usage = CLAUDE.parse_usage(
        (support.FIXTURES / "claude" / "usage_partial.SYNTHETIC.result.json").read_text(encoding="utf-8")
    )
    return {
        "claude": {"usage": usage},
        "claude_api": {"usage": unknown_usage("API credit balance is not queried")},
        "cursor": {"usage": unknown_usage()},
    }


class ClaudePoolTest(unittest.TestCase):
    def test_subscription_pool_strips_api_key(self):
        settings = settings_with(
            first_tool="claude_subscription",
            tools={"claude": {"enabled": True, "plan": "included"}},
        )
        result = choose(
            {"difficulty": "normal", "bytes_in_scope": 0, "roundtrip_tokens": 0},
            settings,
            reports(),
            load_catalog(),
        )
        self.assertEqual(result["tool"], "claude")
        self.assertEqual(result["billing_pool"], "claude_subscription")
        self.assertEqual(result["launch"]["auth"], "claude_subscription")
        self.assertEqual(result["launch"]["unset_env"], ["ANTHROPIC_API_KEY"])
        self.assertNotIn("require_env", result["launch"])

    def test_api_pool_requires_key_but_never_contains_it(self):
        settings = settings_with(
            first_tool="claude_api",
            extra_spend="per_job",
            tools={
                "claude": {"enabled": False},
                "claude_api": {"enabled": True, "plan": "extra"},
            },
        )
        result = choose(
            {
                "difficulty": "normal",
                "bytes_in_scope": 0,
                "roundtrip_tokens": 0,
                "allow_extra_spend": True,
            },
            settings,
            reports(),
            load_catalog(),
        )
        self.assertEqual(result["tool"], "claude_api")
        self.assertEqual(result["billing_pool"], "claude_api")
        self.assertEqual(result["launch"]["auth"], "anthropic_api_key")
        self.assertEqual(result["launch"]["require_env"], ["ANTHROPIC_API_KEY"])
        self.assertNotIn("unset_env", result["launch"])
        self.assertNotIn("sk-ant", str(result))

    def test_api_pool_is_fail_closed_by_default(self):
        settings = settings_with(
            first_tool="claude_api",
            tools={
                "claude": {"enabled": False},
                "claude_api": {"enabled": True},
            },
        )
        result = choose(
            {"difficulty": "normal", "bytes_in_scope": 0, "roundtrip_tokens": 0},
            settings,
            reports(),
            load_catalog(),
        )
        self.assertEqual(result["action"], "stop")
        self.assertTrue(
            any(row["tool"] == "claude_api" and "extra spend" in row["reason"] for row in result["skipped"])
        )

    def test_subscription_alias_normalizes_to_existing_claude_id(self):
        settings = settings_with(first_tool="claude_subscription")
        self.assertEqual(settings["routing"]["first_tool"], "claude")


if __name__ == "__main__":
    unittest.main()
