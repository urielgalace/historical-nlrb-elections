# Contributing

Thank you for helping improve the dataset. The most useful contributions fill known gaps:
election results, plant locations, and industries. Every suggestion needs a source that someone
else can check.

## Suggesting a correction

- **One correction:** use the form on the Contribute page of the website, or open an issue
  with the "Data correction" template. Election IDs are shown on the Data page.
- **Many corrections:** fill in `corrections/TEMPLATE.csv`, one row per change, and attach it to
  an issue.
- **Pull request:** add a CSV file to `corrections/pending/` in the format described in
  `corrections/README.md`. The automatic check runs on every pull request.

Accepted changes are credited by name (or anonymously, if you prefer) in the release that
applies them.

## For project members: reviewing a suggestion

1. Check the source. Does it support the proposed value for this election, and not a different
   plant or year?
2. Add the accepted change to a CSV file in `corrections/pending/`, keeping the contributor's
   source and credit. Close the issue with a note that it will be in the next release.
3. When there are enough changes, make a release (see "Making a new release" in `README.md`).

## Editing the website

- Page text lives in `docs/content/*.md`. `{{n_elections}}` and similar tokens are filled from
  `docs/data/site/aggregates.json`; a token the site does not know shows up as written, so it is
  easy to spot.
- Do not edit `docs/data/site/*.json` or anything in `docs/data/releases/` by hand. The scripts
  write them.
- Preview locally with `cd docs && python3 -m http.server 8000`.
