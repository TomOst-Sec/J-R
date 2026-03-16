# TASK-014: Twitter/X platform module

**Priority:** high
**Milestone:** 1
**Team:** any
**Depends:** TASK-004
**Estimated Complexity:** high

## Description

Implement the Twitter/X platform module. Since Twitter's API requires paid access, use web scraping via Playwright for profile data and the Nitter instances for fallback.

## Requirements

1. Create `src/argus/platforms/twitter.py`:
   - `TwitterPlatform(BasePlatform)`:
     - `name = "twitter"`, `base_url = "https://x.com"`, `rate_limit_per_minute = 10`, `requires_auth = False`, `requires_playwright = True`, `priority = 90`

   - `check_username(username)`:
     - Attempt HEAD request to `https://x.com/{username}`
     - If blocked, try nitter instance: `https://nitter.net/{username}`
     - Return True if 200 (profile exists), False if 404, None if blocked/error

   - `search_name(name, location)`:
     - Use Google dorking: `site:x.com "{name}" "{location}"` via search URL
     - Parse results to extract Twitter profile URLs
     - Return as CandidateProfile list
     - If Playwright available: search `https://x.com/search?q={name}&f=user`

   - `scrape_profile(url)`:
     - Requires Playwright for full profile data
     - Navigate to profile URL, wait for content load
     - Extract: username, display_name, bio, location, profile photo URL, follower/following counts, join date, pinned links
     - Fallback: try nitter HTML parsing with beautifulsoup4

   - `scrape_content(url, max_items)`:
     - Playwright: scroll and collect tweets
     - Fallback: nitter RSS/HTML parsing
     - Map to ContentItem: tweet text, timestamp, engagement (likes, retweets, replies)

2. Implement graceful fallback chain: Playwright → Nitter → Google dork
3. Handle: rate limiting, CAPTCHA detection (back off), account suspension detection

## Acceptance Criteria

- Profile check works via at least one method
- Profile scraping extracts all available fields
- Fallback chain works when primary method fails
- Graceful degradation on blocks/CAPTCHAs
- Unit tests with mocked responses
- `uv run pytest tests/test_platform_twitter.py` passes
