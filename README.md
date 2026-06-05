# /reshapex-brief Skill

A Claude Code skill that creates ReshapeX Internal Brief presentations in Google Slides from any content you paste. The template provides the visual format; every word comes from the user.

## What it produces

A real Google Slides file — not markdown in chat. The skill supports up to 5 slides:

| Slot | Layout | Use for |
|------|--------|---------|
| Cover | Always included | Title, client, date badge |
| slide2 | 3×2 card grid | Inventories, audits, comparisons |
| slide3 | 3×2 icon-item list | Capabilities, steps, features |
| slide4 | 2×2 numbered asks | Recommendations, requirements |
| slide5 | 2-column week plan | Sprints, demo plans |

Unused slides are deleted automatically. Footers renumber to match the actual count.

## Prerequisites

- [Claude Code](https://claude.ai/code) — CLI or VSCode extension
- Python 3.10+
- A Google account with access to Google Drive and Google Slides

## Setup

### 1. Clone this repo

```bash
git clone <repo-url>
cd reshapex-brief-skill
```

### 2. Get `credentials.json`

Ask your team lead for the `credentials.json` file (Google OAuth client secret for the ReshapeX Google Cloud project). Place it in the repo root before running setup — or add it manually afterwards:

```
~/.config/reshapex-mcp/credentials.json
```

> `credentials.json` is in `.gitignore` — never commit it.

### 3. Run setup

```bash
chmod +x setup.sh
./setup.sh
```

This will:
- Install the MCP server to `~/.local/share/reshapex-mcp/`
- Create a Python venv with all dependencies
- Copy the skill to `~/.claude/skills/reshapex-brief/`
- Register the MCP server in your Claude Code config

### 4. Restart Claude Code

Close and reopen Claude Code (or reload the VSCode window) so it picks up the new MCP server.

### 5. First use — Google authentication

The first time you run `/reshapex-brief`, the MCP will open a Google OAuth flow in your browser. Sign in with your Google account. Your token is saved to `~/.config/reshapex-mcp/token.json` — this only happens once.

> Each person authenticates with their own Google account. Presentations are created in your personal Google Drive.

## Usage

In any Claude Code conversation, type:

```
/reshapex-brief <your content>
```

Your content can be anything — free text, a table, bullet points, raw notes. Claude maps it to the right slides, writes all the text, and returns a Google Slides URL.

**Examples:**

```
/reshapex-brief Here are the 13 tools our ImagingSource agent has...
```

```
/reshapex-brief Q3 strategy review: we hit 80% of revenue target,
main blocker was onboarding time, next quarter focus is...
```

```
/reshapex-brief [paste a CSV, a doc extract, a Notion page...]
```

## How it works

```
/reshapex-brief  →  Claude (SKILL.md)  →  MCP server (server.py)
                                               ↓
                                      Google Drive API (copy template)
                                               ↓
                                      Google Slides API (replace all text)
                                               ↓
                                         URL returned to chat
```

## Files

```
reshapex-brief-skill/
├── SKILL.md          Claude Code skill definition
├── server.py         MCP server — handles Drive + Slides API calls
├── requirements.txt  Python dependencies
├── setup.sh          One-command installer
└── .gitignore        Keeps credentials out of git
```

## Troubleshooting

**"MCP server not found" after restart**
Run `./setup.sh` again — it safely re-registers the server.

**Google auth fails / browser doesn't open**
On WSL or headless environments, the OAuth URL is printed to the terminal. Copy it and open it in your browser manually.

**Template not found (404)**
The template lives in a ReshapeX Shared Drive. Make sure your Google account has been granted access. Ask your team lead.

**Text shows as black on the dark slide background**
This is a known issue if you're running an older version of `server.py`. Pull the latest and re-run `./setup.sh`.
