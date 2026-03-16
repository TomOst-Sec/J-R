# Project Goals

> **Instructions:** Human fills this file with project requirements.
> ATLAS reads this to generate the roadmap and tasks.
> Update this file whenever goals change — ATLAS will pick up changes on its next cycle.

## Product Description

Product Description
<!-- What are we building? One paragraph. -->
Argus is an open-source, multi-agent OSINT (Open Source Intelligence) platform that takes a person's name — plus optional signals like location, known URLs, email, username, or phone number — and systematically discovers, verifies, and profiles that person across social media platforms, public databases, and the open web. Unlike Sherlock and Maigret which are simple username-existence checkers prone to false positives, Argus is a verification-first system: it uses cross-platform signal correlation (bio text similarity, profile photo perceptual hashing, shared links, posting time-zone analysis, writing style fingerprinting, mutual follower overlap) to probabilistically confirm that discovered accounts actually belong to the target, assigning each match a confidence score from 0.0–1.0 and automatically discarding likely false positives below a configurable threshold. Argus is built as a composable agent pipeline — the core Resolver Agent discovers and verifies accounts, an optional Linker Agent maps connections between the target and a user-specified topic/entity/organization, and an optional Profiler Agent ingests all discovered content to build a ranked behavioral profile (topics, interests, activity levels) classified into professional/personal/public dimensions. Every agent exposes a standardized JSON interface and can run standalone, be chained via CLI pipes, orchestrated by LLM-based agent frameworks (LangChain, CrewAI, AutoGen, Claude tool-use), or called via REST API — making Argus a first-class building block in any intelligence workflow, not just a standalone tool.

## Tech Stack

Core Language:

Python 3.12+ — async-first (asyncio + aiohttp for all network I/O), type-annotated throughout (strict mypy), single-language stack for maximum contributor accessibility
UV for package management (fast, deterministic lockfile, replaces pip/poetry)

Agent Framework:

Custom lightweight agent protocol — each agent is a Python class implementing BaseAgent with async def run(input: AgentInput) -> AgentOutput interface
Agents communicate via typed Pydantic models serialized as JSON (input schemas, output schemas, intermediate results)
Built-in agent orchestrator: sequential pipeline (resolver → linker → profiler), parallel fan-out (run multiple platform scrapers concurrently), conditional branching (skip linker if no topic provided)
LLM integration (optional, not required): agents can optionally call an LLM (OpenAI, Anthropic, Ollama/local) for: bio comparison, content summarization, topic extraction, writing style analysis. All LLM calls go through a unified LLMProvider abstraction. If no LLM is configured, Argus falls back to TF-IDF / cosine similarity / regex-based heuristics — the tool works fully offline without any API keys
MCP (Model Context Protocol) server exposure — Argus runs as an MCP server so Claude Code, Cursor, or any MCP client can invoke it as a tool directly. Exposes tools: resolve_person, link_topic, profile_person, get_results

Scraping & Data Collection:

aiohttp + aiohttp-retry for async HTTP requests with exponential backoff
playwright (async) for JavaScript-rendered pages (Instagram, LinkedIn, Twitter/X) — headless Chromium, stealth mode via playwright-stealth
beautifulsoup4 + lxml for HTML parsing
Platform-specific modules (one Python file per platform): Twitter/X, Instagram, Facebook, LinkedIn, GitHub, Reddit, TikTok, YouTube, Medium, Telegram, Discord (public servers), Mastodon/Fediverse, Stack Overflow, HackerNews, Personal blogs (via Google dorking)
Rate limiting per platform: token bucket algorithm, configurable per-platform delays, automatic backoff on 429/captcha detection
Proxy support: SOCKS5/HTTP proxy rotation via config, optional residential proxy integration
User-Agent rotation from a curated list of 50+ real browser fingerprints

Verification & Matching Engine:

imagehash — perceptual hashing (pHash, dHash, aHash) for profile photo cross-matching
scikit-learn — TF-IDF vectorization + cosine similarity for bio/content text comparison
dateutil + custom timezone inference — analyze posting timestamps to infer timezone (correlate across platforms)
jellyfish — Jaro-Winkler / Levenshtein distance for fuzzy name matching
networkx — graph-based relationship mapping (for Linker Agent)
Custom confidence scoring model: weighted sum of signals (photo match: 0.35, bio similarity: 0.20, timezone correlation: 0.15, username pattern: 0.10, mutual connections: 0.10, writing style: 0.10) — weights configurable in argus.toml

Storage:

SQLite (default) — zero-dependency local storage, one DB file per investigation (~/.argus/investigations/<id>/argus.db)
Schema: targets (id, name, location, seed_urls, created_at), accounts (id, target_id, platform, username, url, confidence, raw_data_json, verified_at), content (id, account_id, text, timestamp, content_type, metadata_json), connections (id, source_account_id, target_entity, relationship_type, evidence_json, confidence), profiles (id, target_id, dimension, topic, activity_score, evidence_json)
Optional PostgreSQL backend for team/server deployments (same schema, switchable via config)
All raw scraped data stored as JSON blobs — full audit trail, re-processable without re-scraping

Output & Reporting:

JSON (primary) — structured output for programmatic consumption and agent chaining
Markdown report — human-readable investigation summary with confidence scores, links, and evidence
HTML report — styled, interactive report with profile photos, timeline, topic charts (uses Jinja2 templates)
CSV export — flat table of all discovered accounts with metadata
Neo4j-compatible graph export (GraphML/JSON) — for visualization in Neo4j, Gephi, or yEd

CLI:

click — CLI framework with subcommands per agent
Rich — terminal formatting (tables, progress bars, colored confidence scores, tree views)
Interactive mode: argus shell drops into an interactive REPL where you can run agents, inspect results, and refine searches

API Server (optional):

FastAPI — REST API exposing all agent operations as endpoints
WebSocket endpoint for streaming results (long-running investigations push results as they're found)
API key auth (simple bearer token) for multi-user server deployments
OpenAPI spec auto-generated

Testing:

pytest + pytest-asyncio — unit tests for each platform module, integration tests for agent pipeline
VCR.py / aioresponses — recorded HTTP cassettes for deterministic testing without live network
Faker — generate synthetic profiles for testing verification logic
Coverage target: >80% on verification engine, >60% on platform modules

CI/CD:

GitHub Actions: lint (ruff), type-check (mypy), test (pytest), build (Docker), release (PyPI + GitHub Releases)
Pre-commit hooks: ruff format, ruff check, mypy



## Features

Resolver Agent — Platform Discovery Engine — The core agent. Takes input: {name: str, location?: str, seed_urls?: str[], email?: str, username_hint?: str, phone?: str}. Step 1: generate username candidates from the name (lowercase, dots, underscores, numbers — common patterns). Step 2: for each supported platform, check username existence via platform-specific methods (API where available, HTTP HEAD/GET for profile URL patterns, search endpoint queries). Step 3: for platforms with search (Twitter, LinkedIn, GitHub, Reddit), also run name-based searches and collect candidate profiles. Step 4: if seed_urls provided, scrape those profiles first to extract ground-truth signals (profile photo, bio, location, links) for cross-matching. Output: list of {platform, username, url, exists: bool, scraped_data: {...}} — raw candidates before verification. Must support 15+ platforms at launch. Each platform is a separate Python module implementing PlatformModule interface (async def check_username(username) -> bool, async def search_name(name, location) -> list[Profile], async def scrape_profile(url) -> ProfileData). New platforms are added by dropping a new file in argus/platforms/.
Verification & Confidence Scoring Engine — The false-positive killer. Takes the raw candidate list from the Resolver and runs multi-signal cross-correlation to assign each candidate a confidence score (0.0–1.0). Signals computed: (a) Profile Photo Match — download all profile photos, compute perceptual hashes (pHash), compare against seed photos and against each other (if 3+ platforms share the same face, high confidence). Optional: face embedding via face_recognition library for higher accuracy. Weight: 0.35. (b) Bio Similarity — extract bio/about text from each platform, compute pairwise TF-IDF cosine similarity. Shared keywords, job titles, locations boost score. Weight: 0.20. (c) Timezone Correlation — analyze posting timestamps (last 50 posts per platform), infer most-active timezone, compare across platforms. If Twitter and GitHub activity clusters align to the same timezone → signal match. Weight: 0.15. (d) Username Pattern — if the target uses johndoe on Twitter and johndoe_dev on GitHub, the shared root pattern is a signal. Jaro-Winkler similarity between usernames across platforms. Weight: 0.10. (e) Mutual Connections — if discovered accounts follow/friend each other cross-platform (e.g., Twitter bio links to GitHub), strong confirmation signal. Weight: 0.10. (f) Writing Style — average sentence length, vocabulary richness, emoji usage frequency, hashtag patterns. Compare across platforms using cosine similarity on feature vectors. Weight: 0.10. Aggregate score: weighted sum, thresholded at configurable cutoff (default: 0.45 = "possible match", 0.70 = "likely match", 0.90 = "confirmed match"). Accounts below the minimum threshold (default: 0.30) are auto-discarded. All evidence for each signal is stored for human review.
Platform Modules — Async Scrapers — One module per platform, all implementing the same interface. Each module handles platform-specific quirks: rate limits, auth requirements, JavaScript rendering needs, API vs scraping approach. Priority platforms (Milestone 1): Twitter/X (search API + profile scraping via Playwright), GitHub (REST API, no auth needed for public data), Reddit (JSON API, .json suffix trick), LinkedIn (Playwright + Google dork fallback site:linkedin.com/in/ "John Doe"), Instagram (Playwright, login-gated — optional), HackerNews (Algolia API). Milestone 2 platforms: Facebook (limited, Google dork-based), TikTok (Playwright), YouTube (Data API v3), Medium (profile scraping), Telegram (username check via t.me/ probe), Mastodon (WebFinger protocol across instances), Stack Overflow (API), Discord (public server search only). Each module has: retry logic, rate limiting, proxy support, captcha detection (backs off gracefully), and structured output as Pydantic model.
CLI Interface — The primary user interface. Commands: argus resolve "John Doe" --location "Tel Aviv" --seed-url "https://github.com/johndoe" — runs the Resolver + Verification pipeline, outputs table of results sorted by confidence. argus link "John Doe" --topic "CyberSec Company X" — runs Linker Agent on previously resolved results. argus profile "John Doe" — runs Profiler Agent on previously resolved results. argus investigate "John Doe" --full --location "Tel Aviv" — runs all three agents sequentially (resolve → link → profile). argus report "John Doe" --format html — generates a report from stored results. argus platforms — lists all supported platforms and their current status (healthy/rate-limited/blocked). argus config — view/edit configuration. argus shell — interactive REPL mode. All commands support --output json for programmatic consumption. Progress shown via Rich progress bars and live tables (accounts appear in real-time as they're discovered and scored).
Agent Chaining & Orchestration — The agents are composable building blocks. Built-in orchestrator supports: (a) Sequential pipeline: resolver | linker | profiler — output of each feeds into the next. (b) Parallel fan-out: within the Resolver, all platform checks run concurrently (asyncio.gather). (c) Conditional: argus investigate --skip-linker skips the Linker if no topic is provided. (d) External orchestration: each agent can be imported as a Python library (from argus.agents import ResolverAgent; agent = ResolverAgent(); results = await agent.run(input)). (e) Stdin/stdout piping: argus resolve "John Doe" --output json | argus link --topic "AI Startups" --input - — Unix pipe-friendly. (f) MCP server mode: argus serve --mcp exposes all agents as MCP tools for LLM-based orchestrators. (g) REST API mode: argus serve --api starts a FastAPI server. (h) LangChain/CrewAI tool wrappers: optional argus.integrations.langchain and argus.integrations.crewai modules that wrap each agent as a Tool with proper schema definitions.
Linker Agent — Topic Connection Mapper — Optional agent that takes: the resolved accounts + a topic/entity/organization name. Scans all collected content (posts, bios, repos, articles) for mentions of, connections to, or relationships with the specified topic. Methods: (a) keyword/phrase search across all content, (b) semantic similarity (if LLM available: ask "does this content relate to [topic]?"; if offline: TF-IDF cosine against topic description), (c) GitHub: check repos, stars, contributions related to topic, (d) LinkedIn: job history mentions, (e) following/follower overlap with known accounts of the topic entity. Output: {connections: [{platform, content_snippet, relationship_type: "mention"|"employment"|"contribution"|"following"|"endorsement", confidence, url, timestamp}], summary: str}. Relationship types: "mentioned in post", "works/worked at", "contributed to repo", "follows official account", "endorsed by", "attended event", "co-authored with". Connections ranked by strength.
Profiler Agent — Behavioral Profile Builder — Optional agent that ingests all discovered content and builds a comprehensive behavioral profile. Step 1: Content Collection — aggregate all posts, bios, repos, articles, comments across all verified platforms. Step 2: Topic Extraction — use TF-IDF keyword extraction (or LLM-based topic modeling if available) to identify recurring themes. Group topics into clusters. Step 3: Activity Scoring — for each topic, compute an activity score based on: frequency of mentions, recency (recent > old), engagement received (likes, retweets, stars), depth of engagement (wrote an article > retweeted). Step 4: Dimension Classification — classify each topic into one of three dimensions: Professional (job-related, industry, skills, certifications, work projects), Personal (hobbies, interests, family, travel, lifestyle), Public (political views, social causes, community involvement, public statements). Classification via keyword lists + LLM fallback. Step 5: Temporal Analysis — track how topics evolve over time (new interests, career shifts, abandoned hobbies). Output: {dimensions: {professional: [{topic, score, evidence[], trend}], personal: [...], public: [...]}, activity_timeline: [...], top_platforms_by_activity: [...], estimated_timezone: str, posting_frequency: {...}}.
Configuration System — argus.toml config file at ~/.argus/argus.toml (or project-local ./argus.toml). Sections: [general] (default_threshold, max_concurrent_requests, output_format, language), [platforms] (per-platform enable/disable, custom rate limits, credentials if needed), [proxy] (proxy URL, rotation strategy, auth), [llm] (provider: openai|anthropic|ollama|none, model, api_key, base_url), [verification] (signal weights, minimum_confidence_threshold, photo_matching_enabled, face_recognition_enabled), [output] (default_format, report_template, include_raw_data), [api] (host, port, api_key, cors_origins). All config values overridable via CLI flags and environment variables (ARGUS_LLM_PROVIDER=ollama). Sensitive values (API keys) support env var references in config: api_key = "${OPENAI_API_KEY}".
Report Generator — Produces human-readable investigation reports in multiple formats. JSON: raw structured data, used for agent chaining and programmatic access. Markdown: clean report with sections: Executive Summary (one paragraph), Discovered Accounts (table: platform, username, URL, confidence, key evidence), Topic Profile (if Profiler ran — ranked topics by dimension), Connections (if Linker ran — topic relationship map), Timeline (key activities chronologically), Methodology (which agents ran, which signals were used, what thresholds). HTML: styled interactive report using Jinja2 template — includes embedded profile photos (base64), clickable links, collapsible evidence sections, confidence score color-coding (red/yellow/green), interactive topic chart (Chart.js bar chart of topics by activity score per dimension). CSV: flat export of all accounts for spreadsheet analysis. GraphML: node-edge export for graph visualization tools — nodes are accounts, edges are cross-platform confirmation signals and topic connections.
MCP Server Mode — argus serve --mcp starts Argus as a Model Context Protocol server (stdio transport). Exposes tools: resolve_person (input: name, location, seed_urls → output: verified accounts with confidence), link_topic (input: investigation_id, topic → output: connections), profile_person (input: investigation_id → output: behavioral profile), get_investigation (input: investigation_id → output: full results), list_investigations → output: all stored investigations). This makes Argus a first-class tool for LLM agents — Claude Code can call resolve_person("John Doe", location="SF") directly. MCP resources: expose investigation reports as readable resources. MCP prompts: pre-built prompt templates for common OSINT workflows.
REST API Server — argus serve --api --port 8000 starts a FastAPI server. Endpoints: POST /investigate (start new investigation, returns investigation_id), GET /investigate/{id} (get results), GET /investigate/{id}/report?format=html (get rendered report), POST /resolve (run resolver only), POST /link (run linker only), POST /profile (run profiler only), GET /platforms (list platform status), WS /investigate/{id}/stream (WebSocket streaming results as they arrive). All endpoints accept/return JSON. Bearer token auth. CORS configurable. OpenAPI spec at /docs. Rate limited (configurable). Designed for: web UI frontends, team deployments, integration with security operations platforms (SOAR/SIEM), webhook triggers.
Investigation Persistence & Resume — Every investigation is persisted to SQLite as it runs. If Argus crashes or is interrupted (Ctrl+C), resuming with the same input picks up where it left off — already-scraped platforms are skipped, already-verified accounts retain their scores. Investigations are identified by a hash of (name, location, seed_urls). argus investigations list shows all past investigations. argus investigations resume <id> continues a stopped investigation. argus investigations delete <id> removes all stored data. Data retention: configurable auto-purge after N days (default: 90). Export: argus investigations export <id> --format json dumps everything for archival.
Stealth & Anti-Detection — Platforms actively block scrapers. Argus minimizes detection via: (a) Realistic request patterns — random delays between requests (configurable range, default 2-5s between profile loads), human-like navigation sequences in Playwright (scroll, hover, natural click patterns). (b) Browser fingerprint rotation — Playwright stealth patches (navigator.webdriver=false, realistic viewport/language/platform), User-Agent rotation from curated list. (c) Proxy rotation — round-robin or random selection from proxy pool, sticky sessions per platform (same IP for a logical session). (d) Rate limit respect — per-platform token bucket, automatic backoff on 429, exponential wait on captcha detection. (e) Session management — reuse Playwright browser contexts (cookies, localStorage) to mimic logged-in browsing where appropriate. (f) Graceful degradation — if a platform blocks, log it, mark platform as "blocked" for cooldown period, continue with other platforms. Never crash on a single platform failure.
Extensible Platform Plugin System — Adding a new platform should take <30 minutes for a developer. Each platform is a single Python file in argus/platforms/ that subclasses BasePlatform. Required methods: check_username(username) -> bool | None, search_name(name, location) -> list[CandidateProfile], scrape_profile(url) -> ProfileData. Optional methods: scrape_content(url, max_items) -> list[ContentItem], get_connections(url) -> list[Connection]. Auto-discovery: any .py file in the platforms directory that subclasses BasePlatform is automatically registered. Platform metadata via class attributes: name, base_url, rate_limit_per_minute, requires_auth, requires_playwright, priority (higher = checked first). Community platforms can be installed as pip packages: pip install argus-platform-vk adds VK support.
Privacy & Ethics Safeguards — Argus is a defensive OSINT tool, not a stalking tool. Built-in safeguards: (a) Scope limiting — configurable maximum platforms to check, maximum content items to collect, maximum investigation time. (b) Audit logging — every action is logged with timestamp, reason, and operator identifier. Logs stored alongside investigation data. (c) Consent flag — optional --authorized flag that must be explicitly set; without it, Argus prints a reminder about legal/ethical use and requires confirmation. (d) No credential stuffing — Argus never attempts to log into accounts, crack passwords, or access private data. Only publicly visible information is collected. (e) robots.txt respect — optional flag to check and respect robots.txt before scraping. (f) Data minimization — by default, raw content is summarized rather than stored verbatim. --store-raw flag explicitly opts into full content storage. (g) Right to be forgotten — argus investigations purge-person "John Doe" deletes ALL stored data about a person across all investigations.

## Milestones

### Milestone 1: MVP

<!-- Group features into milestones with rough ordering -->
Milestone 1: MVP (Week 1-2) — "Find the person, prove it's them"

Resolver Agent core (Feature 1) — username candidate generation, platform existence checks
6 Priority Platform Modules (Feature 3 subset) — Twitter/X, GitHub, Reddit, LinkedIn, Instagram, HackerNews — each with check_username + search_name + scrape_profile
Verification Engine (Feature 2) — profile photo perceptual hashing, bio similarity (TF-IDF), username pattern matching, confidence scoring with configurable weights
CLI: argus resolve command (Feature 4 subset) — name input, --location, --seed-url flags, Rich table output showing platform/username/url/confidence, --output json
SQLite persistence (Feature 12 subset) — store investigation results, resume interrupted runs
Configuration (Feature 8 subset) — argus.toml with platform enables, rate limits, proxy, thresholds
Basic stealth (Feature 13 subset) — User-Agent rotation, per-platform rate limiting, random delays
Platform plugin interface (Feature 14) — BasePlatform class, auto-discovery from platforms directory
Ship criteria: argus resolve "John Doe" --location "Tel Aviv" --seed-url "https://github.com/johndoe" finds accounts across 6 platforms, filters false positives with >75% precision, shows confidence scores, completes in <60 seconds. A developer can add a new platform in <30 minutes.

### Milestone 2: Core Features

Linker Agent (Feature 6) — topic connection mapping across all discovered content, keyword + semantic search, relationship type classification, ranked connection output
Profiler Agent (Feature 7) — topic extraction, activity scoring, professional/personal/public dimension classification, temporal analysis
Agent chaining & orchestration (Feature 5) — sequential pipeline, parallel fan-out, stdin/stdout piping, Python library import interface
Full CLI (Feature 4) — all commands: resolve, link, profile, investigate (full pipeline), report, platforms, config, shell (REPL)
8 additional platform modules (Feature 3) — Facebook, TikTok, YouTube, Medium, Telegram, Mastodon, Stack Overflow, Discord
Report generator (Feature 9) — JSON, Markdown, HTML (styled with Jinja2 + Chart.js), CSV, GraphML
LLM integration (optional) (Feature 8 enhancement) — unified LLMProvider abstraction, OpenAI/Anthropic/Ollama support, fallback to offline heuristics
Timezone correlation signal (Feature 2 enhancement) — posting time analysis, timezone inference
Writing style signal (Feature 2 enhancement) — stylometric feature extraction, cross-platform comparison
Investigation persistence & resume (Feature 12) — full implementation, list/resume/delete/export commands
Ship criteria: argus investigate "John Doe" --full --topic "CyberSecurity" --location "Tel Aviv" runs all three agents, produces a comprehensive HTML report with discovered accounts, topic connections, behavioral profile with professional/personal/public dimensions, all in <5 minutes. Agents can be chained via CLI pipes or Python imports.

### Milestone 3: Polish

MCP Server Mode (Feature 10) — stdio transport, all agents as MCP tools, investigation resources, prompt templates
REST API Server (Feature 11) — FastAPI, all endpoints, WebSocket streaming, auth, OpenAPI spec
LangChain/CrewAI tool wrappers (Feature 5 enhancement) — proper Tool schema definitions, example notebooks
Playwright stealth hardening (Feature 13) — full anti-detection suite, captcha detection + graceful backoff, proxy rotation with sticky sessions
Privacy safeguards (Feature 15) — audit logging, consent flag, data minimization, purge commands, robots.txt option
Mutual connections signal (Feature 2 enhancement) — cross-platform follow/friend graph analysis
Face recognition (optional Feature 2 enhancement) — face_recognition library integration for higher-accuracy photo matching
Performance optimization — connection pooling, concurrent platform scraping tuning, caching for repeated investigations
Documentation — full README with examples, architecture guide, platform module development guide, API reference, agent integration cookbook
Docker image — docker run argus resolve "John Doe" works out of the box, multi-stage build, <200MB image
Ship criteria: Argus runs as an MCP tool inside Claude Code. Argus runs as a LangChain tool inside a CrewAI crew. REST API serves a team of analysts. Documentation is comprehensive enough for a new contributor to add a platform module without reading source code. Docker image runs on any machine.

### Milestone 4: Advanced

Network Expansion Agent — given a resolved person, discover their social graph (followers, following, co-authors, co-contributors) and optionally resolve those connections too (depth-limited BFS across social graphs — configurable max depth, max nodes)
Batch Investigation — argus batch people.csv processes a list of names in parallel, deduplicates shared connections, outputs aggregate network graph
Change Detection — argus watch "John Doe" --interval 24h periodically re-checks all discovered accounts for new content, profile changes, new accounts. Sends notifications (webhook, email, Slack) on changes
Custom scoring models — train a logistic regression / small classifier on labeled true/false positive data from past investigations to improve confidence scoring per deployment
Web UI — lightweight single-page app (Svelte or vanilla JS) that wraps the REST API — investigation dashboard, interactive graph visualization (D3.js force-directed), report viewer, platform status monitor
Encrypted storage — optional at-rest encryption for investigation databases (SQLCipher or application-level AES-256-GCM)
Multi-language content analysis — support for non-English content in topic extraction and writing style analysis (Hebrew, Arabic, Russian, Chinese, Spanish, French — using langdetect + language-specific NLP models)
Ship criteria: Argus can map a person's entire professional network (2 hops), detect changes in their online presence, and serve a team of analysts via a web dashboard. Suitable for professional OSINT operations.

## Constraints

Works fully offline (no LLM required). Every feature must function without any API keys, cloud services, or internet-connected AI models. The LLM integration is a quality enhancer, not a dependency. All verification signals, topic extraction, dimension classification, and report generation work with pure algorithmic approaches (TF-IDF, cosine similarity, regex patterns, keyword lists, perceptual hashing). If [llm] provider = "none" in config (the default), Argus runs entirely locally with zero network calls except to target platforms.
<60 second full resolve for 15 platforms. The Resolver Agent must complete username checks + name searches + profile scraping across all 15 platforms in under 60 seconds with default rate limits. This requires concurrent async I/O — all platforms are scraped in parallel (asyncio.gather), with per-platform rate limiting handled independently. Single-platform check: <3 seconds. Full pipeline (resolve + verify + link + profile): <5 minutes.
>75% precision on verification. Of accounts marked as "likely match" (confidence ≥0.70), at least 75% must be true positives when evaluated on a test set of 50 real-world investigations. False positive rate at the default threshold (0.45) must be <30%. These metrics are tracked via a labeled test dataset maintained in the repo (tests/fixtures/ground_truth/).
Zero PII leakage in logs/output. Log files must never contain scraped content, profile photos, or personally identifiable information. Logs contain only: platform names, action types, timestamps, success/failure, and error messages. All PII stays in the SQLite investigation database, which is local and user-controlled.
Graceful degradation per platform. If a platform blocks, rate-limits, goes down, or changes its HTML structure, Argus must: (a) log the failure, (b) mark the platform as unavailable for a cooldown period, (c) continue the investigation on all other platforms without interruption. A single platform failure must never crash the process or corrupt investigation state. The CLI shows a warning, not an error.
Agent interface stability. The BaseAgent interface (async def run(input: AgentInput) -> AgentOutput) and the Pydantic input/output models are the public API contract. These must remain backward-compatible across minor versions. Breaking changes require a major version bump. This is critical because external agent frameworks (LangChain, CrewAI, MCP clients) depend on stable schemas.
No credential stuffing or private data access. Argus must never: attempt to log into accounts it doesn't own, brute-force passwords, access private/protected posts, exploit API vulnerabilities, or circumvent access controls. Only publicly visible information is collected. The code must be auditable for this constraint — no obfuscated scraping logic.
Reproducible investigations. Running the same investigation twice (same name, location, seed URLs) must produce consistent results (modulo platform changes between runs). All randomness (delays, User-Agent selection) uses a seeded PRNG per investigation for reproducibility. Investigation parameters and environment are recorded in the output for auditability.
Cross-platform (macOS, Linux, Windows). All functionality must work on all three major OSes. Playwright handles browser differences. File paths use pathlib. No OS-specific system calls. CI tests on all three platforms.
Single pip install argus-osint or uvx argus-osint. The core tool (Resolver + Verification + CLI) must install with zero system dependencies beyond Python 3.12+. Playwright browsers are auto-installed on first run (playwright install chromium). Optional dependencies (face_recognition, LLM providers) are extras: pip install argus-osint[face], pip install argus-osint[llm], pip install argus-osint[api].
MIT License. Fully open source. No proprietary dependencies. No CLA.

## Out of Scope

Not a hacking tool. Argus does not exploit vulnerabilities, perform credential stuffing, access private accounts, decrypt data, or bypass security controls. It only collects publicly available information through the same methods a human would use (viewing public profiles, searching public posts).
Not a real-time surveillance system. The watch/monitoring feature (Milestone 4) is periodic re-checking, not real-time streaming. Argus does not maintain persistent connections to platforms or intercept communications.
Not a face recognition service. Profile photo matching uses perceptual hashing by default (fast, no ML). The optional face_recognition integration is a supplementary signal, not a face-ID system. Argus does not build facial recognition databases or do one-to-many face searches against scraped photos.
Not a data broker. Argus does not aggregate, resell, or expose collected data to third parties. All data stays local (SQLite) or on the operator's own server (Postgres). No telemetry, no phoning home, no data sharing.
Not a dark web / Tor scraper. Argus only operates on the clear web. No .onion crawling, no dark web marketplace scraping, no Tor integration. If a future contributor wants this, it's a separate tool.
Not a social engineering framework. Argus discovers and profiles — it does not generate phishing messages, fake profiles, impersonation content, or social engineering playbooks. The Profiler Agent builds an analytical profile, not an attack profile.
Not handling paid/premium platform APIs. Argus uses only free API tiers and public scraping. It does not integrate with paid OSINT databases (Pipl, Spokeo, BeenVerified, TLOxp) or premium social media API tiers (Twitter Enterprise, LinkedIn Sales Navigator). If someone has paid API access, they can build a platform module for it, but it's not in the core.
Not building NLP/ML models from scratch. Topic extraction uses TF-IDF or pre-trained LLMs. Writing style analysis uses simple statistical features. Argus does not train custom ML models — it uses existing libraries and optional LLM calls. The verification confidence model is a weighted sum, not a trained classifier (until Milestone 4's optional custom scoring).
Not a web scraping framework. Argus is an OSINT tool that happens to scrape. It is not a general-purpose web scraper, crawling framework, or data extraction pipeline. The scraping layer is purpose-built for social media profiles and optimized for OSINT workflows.
Not supporting real-time collaboration. Multi-user access via the REST API is supported, but there is no real-time collaborative investigation (shared cursors, live co-editing, conflict resolution). Each investigation is owned by one operator. Team workflows use the API with separate client sessions.
