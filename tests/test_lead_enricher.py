import pytest
from intelligence.lead_enricher import is_bot_wall


def test_is_bot_wall_empty():
    assert is_bot_wall("", "http://example.com") is False


def test_is_bot_wall_clean():
    clean_text = "Welcome to our beautiful website. Contact us at info@example.com."
    assert is_bot_wall(clean_text, "http://example.com") is False


def test_is_bot_wall_with_signal():
    text = "Please Verify You Are Human to continue."
    assert is_bot_wall(text, "http://example.com") is True


def test_is_bot_wall_with_cloudflare():
    text = "Checking your browser before accessing example.com."
    assert is_bot_wall(text, "http://example.com") is True


def test_is_bot_wall_mixed_case():
    text = "Attention REQUIRED! 403 FORBIDDEN!"
    assert is_bot_wall(text, "http://example.com") is True


def test_is_bot_wall_only_in_url():
    # Since the function currently only checks text, a signal in the URL shouldn't trigger it
    # unless it's also in the text.
    assert is_bot_wall("Hello world", "http://example.com/captcha") is False


def test_is_bot_wall_none_text():
    # Should probably raise AttributeError since it calls text.lower()
    with pytest.raises(AttributeError):
        is_bot_wall(None, "http://example.com")


def test_is_bot_wall_various_signals():
    # Test a few other signals to be comprehensive
    assert is_bot_wall("DDoS protection by Cloudflare", "http://example.com") is True
    assert (
        is_bot_wall("Please wait, checking your browser...", "http://example.com")
        is True
    )
    assert is_bot_wall("Enable cookies to continue", "http://example.com") is True
