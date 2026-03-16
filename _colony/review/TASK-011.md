# TASK-011: HackerNews platform module

**Priority:** high
**Milestone:** 1
**Team:** any
**Depends:** TASK-004
**Estimated Complexity:** medium

## Description

Implement the HackerNews platform module using the Algolia HN Search API.

## Requirements

1. Create `src/argus/platforms/hackernews.py`:
   - `HackerNewsPlatform(BasePlatform)`:
     - `name = "hackernews"`, `base_url = "https://news.ycombinator.com"`, `rate_limit_per_minute = 30`, `requires_auth = False`, `requires_playwright = False`, `priority = 60`

   - `check_username(username)`:
     - GET `https://hacker-news.firebaseio.com/v0/user/{username}.json`
     - Return True if response is not null, False otherwise

   - `search_name(name, location)`:
     - GET `https://hn.algolia.com/api/v1/search?query={name}&tags=ask_hn,show_hn,comment`
     - Extract unique authors, return as CandidateProfile list

   - `scrape_profile(url)`:
     - Extract username from URL
     - GET `https://hacker-news.firebaseio.com/v0/user/{username}.json`
     - Map: id→username, about→bio (strip HTML), created→join_date, karma→metadata
     - Profile photo: HN has no photos — set to None

   - `scrape_content(url, max_items)`:
     - GET user's submitted item IDs, fetch top N items
     - Or use Algolia: `https://hn.algolia.com/api/v1/search?tags=author_{username}&hitsPerPage={max_items}`
     - Map: title/text→text, created_at→timestamp, story/comment→content_type, url→url, points→engagement

## Acceptance Criteria

- All interface methods implemented
- Firebase API and Algolia API both used appropriately
- HTML stripped from `about` field
- Unit tests with mocked HTTP responses
- `uv run pytest tests/test_platform_hackernews.py` passes

---
Claimed-By: alpha-1
Completed-At: 2026-03-17T00:00:00+02:00
