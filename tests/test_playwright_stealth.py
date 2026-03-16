"""Tests for Playwright stealth hardening."""

from argus.stealth.browser_profiles import BrowserProfile, get_random_profile
from argus.stealth.playwright_stealth import StealthBrowser, _CAPTCHA_INDICATORS, _STEALTH_SCRIPTS


class TestBrowserProfiles:
    def test_get_random_profile(self):
        profile = get_random_profile()
        assert isinstance(profile, BrowserProfile)
        assert profile.viewport_width > 0
        assert profile.viewport_height > 0
        assert len(profile.user_agent) > 10
        assert len(profile.language) > 0

    def test_deterministic_with_seed(self):
        p1 = get_random_profile(seed=42)
        p2 = get_random_profile(seed=42)
        assert p1.viewport_width == p2.viewport_width
        assert p1.user_agent == p2.user_agent
        assert p1.timezone == p2.timezone

    def test_different_seeds_different_profiles(self):
        p1 = get_random_profile(seed=1)
        p2 = get_random_profile(seed=999)
        assert p1.user_agent != p2.user_agent or p1.viewport_width != p2.viewport_width

    def test_user_agent_realistic(self):
        profile = get_random_profile()
        assert "Mozilla" in profile.user_agent
        assert "python" not in profile.user_agent.lower()

    def test_viewport_common_resolution(self):
        profile = get_random_profile()
        assert profile.viewport_width >= 1280
        assert profile.viewport_height >= 720

    def test_twenty_unique_profiles(self):
        profiles = [get_random_profile(seed=i) for i in range(20)]
        user_agents = {p.user_agent for p in profiles}
        # Should have some variety
        assert len(user_agents) >= 5


class TestStealthBrowser:
    def test_init_with_profile(self):
        profile = get_random_profile(seed=42)
        browser = StealthBrowser(profile=profile)
        assert browser.profile == profile

    def test_init_with_seed(self):
        browser = StealthBrowser(seed=42)
        assert browser.profile is not None

    def test_default_init(self):
        browser = StealthBrowser()
        assert isinstance(browser.profile, BrowserProfile)


class TestStealthScripts:
    def test_webdriver_patch(self):
        assert "webdriver" in _STEALTH_SCRIPTS
        assert "false" in _STEALTH_SCRIPTS

    def test_chrome_object(self):
        assert "window.chrome" in _STEALTH_SCRIPTS

    def test_plugins_spoofed(self):
        assert "plugins" in _STEALTH_SCRIPTS

    def test_languages_set(self):
        assert "languages" in _STEALTH_SCRIPTS


class TestCaptchaIndicators:
    def test_indicators_defined(self):
        assert len(_CAPTCHA_INDICATORS) >= 5

    def test_recaptcha_detected(self):
        assert "recaptcha" in _CAPTCHA_INDICATORS

    def test_hcaptcha_detected(self):
        assert "hcaptcha" in _CAPTCHA_INDICATORS

    def test_cloudflare_detected(self):
        assert "cf-challenge" in _CAPTCHA_INDICATORS
