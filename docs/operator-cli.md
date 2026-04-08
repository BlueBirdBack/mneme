# Mneme Operator CLI

Mneme now has one obvious operator entrypoint:

- `scripts/mneme.py`

## Why

The repo already had the real building blocks.
The missing piece was one stable command surface instead of a bag of scripts.

## Commands

```bash
./scripts/mneme.py check
./scripts/mneme.py ingest --root ~/.openclaw/workspace --out ./raw
./scripts/mneme.py compile --root ~/.openclaw/workspace --raw ./raw --out ./compiled
./scripts/mneme.py scrub --root ~/.openclaw/workspace
./scripts/mneme.py drift --root ~/.openclaw/workspace
./scripts/mneme.py retrieve --root ~/.openclaw/workspace --query "bdeep geo"
./scripts/mneme.py run --root ~/.openclaw/workspace --out ./compiled
```

This is a thin wrapper, not a second implementation.
The boring underlying scripts stay canonical.
