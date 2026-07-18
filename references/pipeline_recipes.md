# Pipeline recipes

These examples use only commands implemented by version 1.3.x. All results are JSON;
use `jq` or another JSON parser instead of scraping stderr.

## Sources to article

```bash
notebooklm-pipeline research-to-article \
  --sources https://example.com/official https://example.com/independent \
  --files ./paper.pdf \
  --title "Evidence review" \
  --language en \
  --audience "technical decision makers" \
  --tone "precise and skeptical" > article-result.json
```

The workflow asks five evidence questions and then requests a grounded article. Check
`.status`, `.source_summary`, every `.research_findings[].status`, and
`.article.status` before using the draft.

## Sources to social drafts

```bash
notebooklm-pipeline research-to-social \
  --sources https://example.com/a https://example.com/b \
  --platform threads \
  --language zh-TW \
  --variants 3 > social-result.json
```

Supported platforms are `threads`, `twitter`, `linkedin`, `instagram`, and `generic`.
The result is a draft for review; this project has no publishing command.

## RSS digest and Q&A

```bash
notebooklm-pipeline batch-digest \
  --rss https://example.com/feed.xml \
  --title "Weekly digest" \
  --max-entries 20 \
  --qa-count 5 \
  --rss-timeout 30 \
  --max-feed-bytes 5000000 > digest-result.json
```

The feed fetch follows HTTP redirects, enforces time and byte limits, parses RSS/Atom,
and ingests individual article URLs. Empty feeds and zero successful sources fail
before question generation.

## Trend research

Install `trend-pulse`, or point at its absolute executable:

```bash
export TREND_PULSE_CMD=/absolute/path/to/trend-pulse
notebooklm-pipeline trend-to-content \
  --geo TW \
  --count 5 \
  --platform threads \
  --language zh-TW \
  --research-mode deep > trends-result.json
```

For each trend the pipeline ingests usable URLs (or descriptive text), runs NotebookLM
web research, imports results, and creates a grounded draft. One topic failing does not
erase successful topics; expect `partial` when appropriate.

## Batch artifact generation

```bash
notebooklm-pipeline generate-all \
  --files ./paper.pdf \
  --types audio slides report mind-map data-table \
  --language en \
  --output-dir ./output \
  --artifact-concurrency 2 \
  --force > artifacts-result.json
```

Generation jobs start first and then finish with bounded concurrency. Use
`--no-wait --no-download` to enqueue jobs without waiting. `--download` cannot be
combined with `--no-wait`.

## Manual deep research plus podcast

```bash
notebooklm-skill create \
  --title "AI coding evidence" \
  --sources https://example.com/study https://example.com/documentation \
  --strict

notebooklm-skill research \
  --notebook "AI coding evidence" \
  --query "Independent productivity and quality findings" \
  --mode deep --max-sources 10

notebooklm-skill podcast \
  --notebook "AI coding evidence" \
  --audio-format debate \
  --audio-length long \
  --instructions "Contrast supportive and skeptical evidence" \
  --output ./output/podcast.m4a
```

For long jobs, enqueue with `generate --type audio --no-wait`, inspect with
`list-artifacts`, then download by exact artifact ID.

## Automation rules

1. Select the profile explicitly in unattended jobs.
2. Parse JSON and stop on nonzero exits.
3. Treat `partial` as review-required, not success.
4. Retain citation metadata alongside generated prose.
5. Limit concurrency and avoid retry storms after quota errors.
6. Use notebook/artifact IDs rather than ambiguous titles.
7. Never add `--force` or deletion confirmation unless overwrite/delete is intended.
