# TASK-015: LinkedIn platform module

**Priority:** high
**Milestone:** 1
**Team:** any
**Depends:** TASK-004
**Estimated Complexity:** high

## Description

Implement the LinkedIn platform module using Playwright for scraping and Google dorking as fallback.

## Requirements

1. Create `src/argus/platforms/linkedin.py`:
   - `LinkedInPlatform(BasePlatform)`:
     - `name = "linkedin"`, `base_url = "https://www.linkedin.com"`, `rate_limit_per_minute = 10`, `requires_auth = False`, `requires_playwright = True`, `priority = 85`

   - `check_username(username)`:
     - GET `https://www.linkedin.com/in/{username}` — check if returns 200 vs 404
     - LinkedIn often requires login — fall back to Google: `site:linkedin.com/in/{username}`
     - Return True/False/None

   - `search_name(name, location)`:
     - Google dork: `site:linkedin.com/in/ "{name}" "{location}"`
     - Parse Google results for LinkedIn profile URLs
     - Return as CandidateProfile list (limit 10)

   - `scrape_profile(url)`:
     - Playwright: navigate to public profile, extract visible data
     - Parse: name, headline (→bio), location, profile photo, connection count
     - Fallback: Google cache or Google snippet data
     - Many fields may be limited without login — handle gracefully

   - `scrape_content(url, max_items)`:
     - LinkedIn public profiles show limited activity
     - Extract: recent posts if visible, articles, activity summary
     - May return empty list if profile is restricted

2. Handle LinkedIn's aggressive anti-scraping:
   - Random delays between actions
   - Detect login walls, back off gracefully
   - Don't attempt login (per privacy/ethics constraints)

## Acceptance Criteria

- Username check works via direct URL or Google fallback
- Name search via Google dorking returns relevant profiles
- Profile scraping extracts available public data
- Handles login walls gracefully (doesn't crash, returns partial data)
- Unit tests with mocked responses
- `uv run pytest tests/test_platform_linkedin.py` passes
