# TASK-016: Instagram platform module

**Priority:** medium
**Milestone:** 1
**Team:** any
**Depends:** TASK-004
**Estimated Complexity:** high

## Description

Implement the Instagram platform module. Instagram is heavily login-gated — this module provides best-effort public data collection.

## Requirements

1. Create `src/argus/platforms/instagram.py`:
   - `InstagramPlatform(BasePlatform)`:
     - `name = "instagram"`, `base_url = "https://www.instagram.com"`, `rate_limit_per_minute = 10`, `requires_auth = False`, `requires_playwright = True`, `priority = 75`

   - `check_username(username)`:
     - GET `https://www.instagram.com/{username}/` with browser-like headers
     - Check response: 200 with valid profile = True, 404 = False, login wall = None
     - Alternative: `https://www.instagram.com/api/v1/users/web_profile_info/?username={username}`

   - `search_name(name, location)`:
     - Google dork: `site:instagram.com "{name}"`
     - Return matching profile URLs as CandidateProfile list

   - `scrape_profile(url)`:
     - Playwright: navigate to profile page
     - Extract from meta tags / JSON-LD / page source: username, full_name, biography, profile_pic_url, follower_count, following_count, external_url
     - Parse `window._sharedData` or `__additionalDataLoaded` JSON if available
     - Fallback: extract from HTML meta tags (og:title, og:description, og:image)

   - `scrape_content(url, max_items)`:
     - Very limited without login — extract visible post thumbnails/captions if any
     - May return empty list for private/restricted accounts

2. Handle Instagram's restrictions:
   - Detect login walls, return partial data
   - Extract maximum info from public HTML/meta tags
   - Rate limit strictly (Instagram is aggressive about blocking)

## Acceptance Criteria

- Username existence check works for public profiles
- Profile scraping extracts available public data
- Handles private/login-gated profiles gracefully
- Unit tests with mocked responses
- `uv run pytest tests/test_platform_instagram.py` passes
