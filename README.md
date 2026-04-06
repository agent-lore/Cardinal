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

## Development

Format, lint, type-check, and test:

```bash
make fmt        # auto-format
make lint       # lint + format check
make typecheck  # pyright
make test       # pytest
make check      # all of the above
```
