from framework import config


def test_get_api_base_accepts_base_url_alias(monkeypatch):
    monkeypatch.setattr(
        config,
        "get_hive_config",
        lambda: {"llm": {"provider": "openai", "model": "glm-5", "base_url": "https://api.z.ai/api/coding/paas/v4"}},
    )
    assert config.get_api_base() == "https://api.z.ai/api/coding/paas/v4"


def test_get_api_base_prefers_api_base_over_base_url(monkeypatch):
    monkeypatch.setattr(
        config,
        "get_hive_config",
        lambda: {
            "llm": {
                "provider": "openai",
                "model": "glm-5",
                "api_base": "https://primary.example/v1",
                "base_url": "https://secondary.example/v1",
            }
        },
    )
    assert config.get_api_base() == "https://primary.example/v1"
