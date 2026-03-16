# TASK-007: GitHub platform module

**Priority:** high
**Milestone:** 1
**Team:** any
**Depends:** TASK-004
**Estimated Complexity:** medium

## Description

Implement the GitHub platform module using the public REST API (no auth required for public data).

## Requirements

1. Create `src/argus/platforms/github.py`:
   - `GitHubPlatform(BasePlatform)`:
     - `name = "github"`, `base_url = "https://github.com"`, `rate_limit_per_minute = 30`, `requires_auth = False`, `requires_playwright = False`, `priority = 80`

   - `check_username(username)`:
     - GET `https://api.github.com/users/{username}`
     - Return True if 200, False if 404, None on error

   - `search_name(name, location)`:
     - GET `https://api.github.com/search/users?q={name}+location:{location}` (location optional)
     - Parse results into `CandidateProfile` list
     - Limit to top 10 results

   - `scrape_profile(url)`:
     - Extract username from URL
     - GET `https://api.github.com/users/{username}`
     - Map JSON response to `ProfileData`: login→username, name→display_name, bio→bio, location→location, avatar_url→profile_photo_url, blog+html_url→links, created_at→join_date, followers→follower_count, following→following_count
     - Store full API response in raw_json

   - `scrape_content(url, max_items)`:
     - GET `https://api.github.com/users/{username}/repos?sort=updated&per_page={max_items}`
     - Map repos to ContentItem: name+description→text, pushed_at→timestamp, "repo"→content_type, html_url→url, stargazers_count+forks→engagement

2. Handle rate limiting: check `X-RateLimit-Remaining` header, back off when low.
3. Respect `aiohttp.ClientSession` passed by platform manager.

## Acceptance Criteria

- All 4 interface methods implemented
- Rate limit header checking works
- Response parsing maps correctly to Pydantic models
- Unit tests with mocked HTTP responses (aioresponses)
- Tests cover: username exists, username not found, search with results, search empty, profile scrape, content scrape, rate limit handling
- `uv run pytest tests/test_platform_github.py` passes
