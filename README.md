<div align="center">

# 👁️ ARGUS

### The All-Seeing OSINT Platform

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Platforms](https://img.shields.io/badge/platforms-64-blueviolet?style=for-the-badge)](#-64-platforms)
[![Intel Sources](https://img.shields.io/badge/intel%20sources-19-orange?style=for-the-badge)](#-intelligence-sources)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)

**Identity resolution · Breach intelligence · Domain recon · Behavioral profiling**

Give Argus a name, email, phone, or domain — it fans out across **64 platforms** and **19 intelligence sources**, cross-correlates everything, and hands you a confidence-scored dossier.

---

</div>

## ⚡ 30-Second Start

```bash
pip install argus-osint          # or: uv add argus-osint
argus resolve "Linus Torvalds"   # find accounts across 64 platforms
```

```
┌──────────┬──────────────┬─────────────────────────────────┬────────────┬───────────┐
│ Platform │ Username     │ URL                             │ Confidence │ Label     │
├──────────┼──────────────┼─────────────────────────────────┼────────────┼───────────┤
│ github   │ torvalds     │ https://github.com/torvalds     │     92%    │ confirmed │
│ gitlab   │ torvalds     │ https://gitlab.com/torvalds     │     78%    │ likely    │
│ keybase  │ torvalds     │ https://keybase.io/torvalds     │     85%    │ confirmed │
│ reddit   │ torvalds     │ https://reddit.com/u/torvalds   │     45%    │ possible  │
└──────────┴──────────────┴─────────────────────────────────┴────────────┴───────────┘
```

---

## 🔥 What Can Argus Do?

```bash
# 🔍 Find someone across 64 platforms
argus resolve "Jane Doe" --location "NYC" --email jane@example.com

# 📧 Investigate an email — breaches, PGP keys, Gravatar, linked accounts
argus intel email "john@example.com"

# 🌐 Recon a domain — WHOIS, DNS, certs, subdomains, Wayback history
argus intel domain "example.com"

# 📱 Phone lookup — carrier, country, line type, validation
argus intel phone "+1-555-123-4567"

# 💀 Breach check — Have I Been Pwned, LeakCheck, IntelX
argus intel breach "john@example.com"

# 🖼️ Image analysis — perceptual hash, EXIF extraction
argus intel image "https://example.com/photo.jpg"

# 🕸️ Full correlation — cross-reference everything
argus correlate "John Doe"

# 🧠 Behavioral profiling — interests, activity patterns, writing style
argus profile "John Doe"

# 🔗 Topic linking — find connections to orgs, topics, interests
argus link "John Doe" --topic "machine learning"

# 📄 Generate reports
argus report "John Doe" --format markdown --output report.md
```

---

## 🌍 64 Platforms

<table>
<tr>
<td>

**🔧 Developer**
- GitHub
- GitLab
- Bitbucket
- Codeberg
- Stack Overflow
- HackerNews
- Keybase
- npm
- PyPI
- crates.io
- RubyGems
- Docker Hub
- Kaggle

</td>
<td>

**📱 Social**
- Twitter/X
- Instagram
- Facebook
- LinkedIn
- Reddit
- Mastodon
- Bluesky
- Threads
- TikTok
- Snapchat
- Pinterest
- Tumblr
- VK

</td>
<td>

**🎬 Media**
- YouTube
- Twitch
- Spotify
- SoundCloud
- Odysee
- Rumble
- PeerTube
- DeviantArt
- Behance
- Dribbble
- 500px
- Flickr

</td>
<td>

**🌐 Other**
- Linktree
- Substack
- Medium
- Patreon
- BuyMeACoffee
- About.me
- Steam
- Lichess
- Chess.com
- Goodreads
- Wikipedia
- Wikidata
- Telegram
- Discord
- Trello
- Strava
- Quora
- Nostr
- Matrix
- Pixelfed
- Gab
- Minds
- HackTheBox
- TryHackMe

</td>
</tr>
</table>

---

## 🕵️ Intelligence Sources

| Category | Sources | What You Get |
|:--------:|---------|:-------------|
| 💀 **Breach** | Have I Been Pwned · LeakCheck · IntelX | Breached credentials, exposed data types |
| 🌐 **Domain** | WHOIS · DNS · crt.sh · SecurityTrails | Registration, records, certs, subdomains |
| 🔒 **Network** | Shodan · VirusTotal · Wayback Machine | Open ports, threat intel, historical snapshots |
| 🪪 **Identity** | PGP Keyservers · Hunter.io · Libravatar · Gravatar | Keys, email verification, avatars |
| 📋 **Records** | OpenCorporates · OCCRP Aleph · Google Dorking | Corporate filings, investigations, targeted queries |
| 📞 **Comms** | Email Validation · Phone Lookup · Paste Search | MX checks, carrier info, paste exposure |

---

## 📦 Install

```bash
pip install argus-osint                  # core
pip install argus-osint[intel]           # + WHOIS, DNS, phone parsing
pip install argus-osint[playwright]      # + browser automation
pip install argus-osint[api]             # + REST API server
pip install argus-osint[all]             # everything
```

<details>
<summary><b>🛠️ Development setup</b></summary>

```bash
git clone https://github.com/TomOst-Sec/Argus-OSINT.git
cd Argus-OSINT
uv sync --group dev
uv run pytest tests/ -x     # run tests
uv run argus platforms       # verify 64 platforms
```
</details>

---

## ⚙️ Configuration

```bash
argus config init   # creates argus.toml
```

```toml
[general]
default_threshold = 0.45
max_concurrent_requests = 10

[stealth]
min_delay = 2.0
max_delay = 5.0

[intel]
hibp_api_key = ""           # haveibeenpwned.com ($3.50/mo)
shodan_api_key = ""         # shodan.io (free tier)
virustotal_api_key = ""     # virustotal.com (free tier)
hunter_api_key = ""         # hunter.io (free tier)
enable_breach_check = true
enable_domain_intel = true
```

Environment overrides: `ARGUS_INTEL_HIBP_API_KEY=xxx`

---

## 🏗️ Architecture

```
                    ┌─────────────────────────────────────────┐
                    │              ARGUS ENGINE                │
                    ├─────────────────────────────────────────┤
  Name / Email ───► │  Resolver ──► Verification ──► Scoring  │ ───► Dossier
  Phone / Domain    │      │            Engine          │      │
                    │      ▼                            ▼      │
                    │  64 Platforms    19 Intel     Correlation │
                    │  (parallel)     Sources       Engine     │
                    ├─────────────────────────────────────────┤
                    │  Stealth Layer: UA rotation, rate limits, │
                    │  proxy support, Camoufox browser          │
                    └─────────────────────────────────────────┘
```

**Verification signals**: photo hash (35%) · bio similarity (20%) · timezone (15%) · username patterns (10%) · connections (10%) · writing style (10%)

---

## 🔌 Integrations

```bash
argus serve --api --port 8000   # REST API (FastAPI + OpenAPI docs)
argus serve --mcp               # MCP server for Claude Code
```

Also integrates with **LangChain** and **CrewAI** as tool providers.

---

<div align="center">

**MIT License** · Built for authorized security research, CTF, and OSINT investigations only.

All sources are **publicly accessible APIs** and **legally queryable services**. No unauthorized access.

</div>
