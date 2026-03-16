# TASK-008: Reddit platform module

**Priority:** high
**Milestone:** 1
**Team:** any
**Depends:** TASK-004
**Estimated Complexity:** medium

## Description

Implement the Reddit platform module using the public JSON API (append `.json` to URLs).

## Requirements

1. Create `src/argus/platforms/reddit.py`:
   - `RedditPlatform(BasePlatform)`:
     - `name = "reddit"`, `base_url = "https://www.reddit.com"`, `rate_limit_per_minute = 20`, `requires_auth = False`, `requires_playwright = False`, `priority = 70`

   - `check_username(username)`:
     - GET `https://www.reddit.com/user/{username}/about.json`
     - Return True if 200 and valid user data, False if 404, None on error
     - Must send a realistic User-Agent header (Reddit blocks default Python UA)

   - `search_name(name, location)`:
     - Reddit has no name search — return empty list
     - If username_hint available, check that directly

   - `scrape_profile(url)`:
     - Extract username from URL
     - GET `https://www.reddit.com/user/{username}/about.json`
     - Map to ProfileData: name→username, subreddit.public_description→bio, icon_img→profile_photo_url, created_utc→join_date, link_karma+comment_karma→metadata
     - Store full response in raw_json

   - `scrape_content(url, max_items)`:
     - GET `https://www.reddit.com/user/{username}.json?limit={max_items}&sort=new`
     - Map posts/comments to ContentItem: title+selftext or body→text, created_utc→timestamp, "post"|"comment"→content_type, permalink→url, ups+num_comments→engagement

2. Handle Reddit-specific quirks:
   - Mandatory User-Agent with app identifier
   - Rate limit: respect 429 responses, back off
   - Handle suspended/shadowbanned accounts (return appropriate response)

## Acceptance Criteria

- All 4 interface methods implemented
- Realistic User-Agent header sent
- Handles suspended/deleted accounts gracefully
- Unit tests with mocked HTTP responses
- Tests cover: user exists, user not found, suspended user, profile scrape, content scrape
- `uv run pytest tests/test_platform_reddit.py` passes

---
Claimed-By: bravo-1
Claimed-At: 2026-03-16T22:59:13+02:00

Completed-At: 2026-03-16T22:59:13+02:00
