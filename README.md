# Cardinal

![Nobody expects the Cardinal](nobody-expects-the-cardinal.png)

Cardinal is an AI-powered code review watchdog that you point at a list of GitHub repos and have it iterate over them, using Claude and Codex to analyse the codebase against open issues — automatically opening or re-opening issues where regressions or unresolved problems are detected. A separate audit phase targets closed issues, checking for incorrect closures and regressions, but keeps itself sane by focusing only on high-severity issues and random-sampling the rest, with a local SQLite database tracking what's been checked and when. Rate limits are handled gracefully — priority queue ensures the most critical repos get coverage first, with model fallback if one hits its cap.

## Getting Started

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Usage

```bash
uv run cardinal hello
uv run cardinal hello --name Cardinal
```

## Configuration

Cardinal reads a TOML file (`cardinal.toml`) at startup. It contains
global settings and an entry per repository to watch. The full annotated
example lives in [cardinal.example.toml](cardinal.example.toml).

### Example

```toml
[cardinal.storage]
db_path = "~/.cardinal/cardinal.db"
clone_dir = "~/.cardinal/repos"

[cardinal.review]
reviewers = ["claude"]
confidence_threshold = 0.7

[cardinal.report]
top_n = 3

[[repos]]
owner_repo = "agent-lore/lithos"
status = "production"
# importance omitted — defaults to "critical" based on status
allow_reopen_closed = true
allow_open_new = true
lithos_project = "projects/lithos"

[[repos]]
owner_repo = "agent-lore/Cardinal"
status = "active"
importance = "critical"   # explicit override
allow_reopen_closed = true
allow_open_new = false
report_top_n = 5

[[repos]]
owner_repo = "agent-lore/ralph-plus-plus"
status = "experimental"
allow_reopen_closed = false
allow_open_new = false
```

### Global config fields

#### `[cardinal.storage]`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `db_path` | string (path) | No | `~/.cardinal/cardinal.db` | Path to the SQLite state database |
| `clone_dir` | string (path) | No | `~/.cardinal/repos` | Root directory for local repo clones |

#### `[cardinal.review]`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `reviewers` | array of strings | No | `["claude"]` | Ordered list of reviewer adapters. Tried in order; falls back on rate limit. Valid values: `claude`, `codex` |
| `confidence_threshold` | float (0.0–1.0) | No | `0.7` | Minimum confidence score a finding must reach before Cardinal acts. Below this, findings are logged but no action is taken. |

#### `[cardinal.report]`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `top_n` | integer ≥ 1 | No | `3` | Number of issues to surface in the per-repo prioritisation report. Overridable per repo. |

### Per-repo config fields (`[[repos]]`)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `owner_repo` | string | **Yes** | — | Repository in `owner/name` format |
| `status` | enum | **Yes** | — | Lifecycle status of the repo (see below) |
| `importance` | enum | No | derived from `status` | How critical this repo is. Overrides the default derived from `status`. |
| `allow_reopen_closed` | bool | No | `false` | Whether Cardinal may reopen closed issues when a regression is detected |
| `allow_open_new` | bool | No | `false` | Whether Cardinal may open new issues when it finds a problem not already tracked |
| `report_top_n` | integer ≥ 1 | No | global `top_n` | Per-repo override for the number of issues in the prioritisation report |
| `lithos_project` | string | No | — | Lithos path prefix for syncing issues to Lithos tasks (e.g. `projects/lithos`) |

### `status` values

| Value | Meaning | Default `importance` |
|-------|---------|---------------------|
| `production` | Live, real users depend on it. Bugs and regressions matter most. | `critical` |
| `active` | In development, being actively worked on. Not yet in users' hands. | `high` |
| `maintenance` | Stable, intentionally not changing much. Occasional fixes only. | `medium` |
| `experimental` | Early exploration or proof-of-concept. Low expectations, high churn. | `low` |
| `dormant` | Paused — not being worked on but may return to it. | `low` |
| `abandoned` | Done with it. Cardinal skips this repo entirely. | — |

### `importance` values

| Value | Internal weight | Meaning |
|-------|-----------------|---------|
| `critical` | 4 | Highest priority. Reviewed first, most aggressive action settings. |
| `high` | 3 | Important. Reviewed early in each run. |
| `medium` | 2 | Normal priority. |
| `low` | 1 | Reviewed last. Conservative defaults. |

### Environment variable overrides

Loaded via `python-dotenv` at startup. **Precedence: env var → config file → built-in default.**

| Env var | Overrides | Notes |
|---------|-----------|-------|
| `CARDINAL_GITHUB_TOKEN` | — | GitHub personal access token. Not stored in the config file. |
| `CARDINAL_CONFIG` | — | Path to `cardinal.toml`. Default search order below. |
| `CARDINAL_DB_PATH` | `cardinal.storage.db_path` | Useful for CI or server deployments. |
| `CARDINAL_REPO_DIR` | `cardinal.storage.clone_dir` | Useful for CI or server deployments. |

Per-repo flags are **not** env-var overridable — they live in the config file only.

### Config file discovery order

When `CARDINAL_CONFIG` is not set, Cardinal looks for `cardinal.toml` in this order:

1. `./cardinal.toml` (current working directory)
2. `~/.cardinal/cardinal.toml` (user home)
3. `/etc/cardinal/cardinal.toml` (system-wide)

First file found wins. Error if none found.

### Validation rules

- `owner_repo` must match `owner/name` format — error at load time
- `status` must be one of the six defined values — error at load time
- `importance` if set must be one of the four defined values — error at load time
- `confidence_threshold` must be between `0.0` and `1.0` inclusive
- `reviewers` must be a non-empty list of known adapter names
- `top_n` and `report_top_n` must be integers ≥ 1
- At least one `[[repos]]` entry is required
- Duplicate `owner_repo` values — error at load time
- GitHub token must be resolvable via `CARDINAL_GITHUB_TOKEN` when a command needs to talk to GitHub

## Docker

### Build the image

```bash
make docker-build
```

### Multi-environment stacks

Cardinal ships with per-environment Docker stacks driven by `.env.<env>` files.
Two environments are supported out of the box: `dev` and `prod`. Each stack runs
with its own Docker Compose project name, container name, and data path, so they
can coexist on the same host.

Set up an environment file:

```bash
cp docker/.env.example docker/.env.dev
# edit docker/.env.dev — fill in CARDINAL_GITHUB_TOKEN
```

Manage the stack with `docker/run.sh`:

```bash
./docker/run.sh dev up        # build and start (detached)
./docker/run.sh dev logs      # follow logs
./docker/run.sh dev status    # show running containers
./docker/run.sh dev restart   # down + up
./docker/run.sh dev down      # stop and remove

./docker/run.sh prod up       # same, for prod
```

Or via Make:

```bash
make docker-up-dev
make docker-down-dev
make docker-up-prod
make docker-down-prod
```

`CARDINAL_ENVIRONMENT` is passed into the container so application code can read
it (e.g. for logging or telemetry labels).

`.env.example` is committed; `.env.dev` and `.env.prod` are gitignored.

## Development

Format, lint, type-check, and test:

```bash
make fmt        # auto-format
make lint       # lint + format check
make typecheck  # pyright
make test       # pytest
make check      # all of the above
```
