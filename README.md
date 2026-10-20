# Historical NLRB Elections, 1936–1960

Union representation elections held under the National Labor Relations Act, rebuilt from the
National Labor Relations Board's published decisions: where each election took place, the
employer's industry, the union, and what is known of the result, with a source for each value.

> **Status: draft for review.** This repository is private and the website is not public yet.
> Text marked "To confirm" or "To decide" on the site needs a decision from the project leads
> before launch.

## What is here

| Path | What it holds |
|---|---|
| `docs/` | The website. GitHub Pages will serve this folder. |
| `docs/data/releases/v1.0/` | Release 1.0: the dataset, codebook, gap lists, held-back tallies, county code fixes, and the research workbooks. A release never changes after it is published. |
| `docs/data/site/` | JSON files the website reads. The scripts generate them; do not edit by hand. |
| `docs/content/` | Text of the Overview, Methods, and Contribute pages, in Markdown. `{{tokens}}` are filled from the release statistics. |
| `corrections/` | Accepted corrections waiting for the next release (`pending/`) and those already applied (`applied/`). |
| `scripts/` | Code that builds releases and checks the data. |
| `data/reference/` | Lookup tables: standard county names with FIPS codes, and SIC titles. |

## Using the data

The current dataset is `docs/data/releases/v1.0/nlrb_elections_v1.0.csv`, one row per election
record (13,673 rows, 46 columns). `codebook_v1.0.csv` describes each column. Please read the
Methods page first. In short:

- Only 18.5% of records have a definite result. Do not compute win rates from this release.
- The dataset covers the elections in the source lists and in published Board decisions, not
  every election the NLRB held.
- Rows marked "Do." in the source lists are separate entries and are kept.

## Making a new release

1. Put accepted corrections in `corrections/pending/` (format in `corrections/README.md`). For
   the RA research worksheet, run
   `python scripts/import_worksheet.py <worksheet.xlsx> --contributor "Name"`.
2. Check them: `python scripts/validate.py`
3. Preview: `python scripts/make_release.py --version 1.1 --date YYYY-MM-DD --title "..." --dry-run`
4. Run the same command without `--dry-run`. It writes `docs/data/releases/v1.1/`, refreshes the
   website data and version history, moves the applied files, and updates `CHANGELOG.md`.
5. Run `python scripts/validate.py` again, review the changes, then commit and push.

Release 1.0 was built from the research workbooks with `scripts/build_release.py`, which needs
pandas and openpyxl. The other scripts use only the Python standard library.

## Previewing the website

```bash
cd docs && python3 -m http.server 8000
```

Then open http://localhost:8000. Opening `index.html` directly from disk does not work, because
the page loads its data with `fetch`.

`docs/data/site/config.json` holds the settings: `repo_url` (turns on the "Open as a GitHub
issue" button), `form_url_template` (a prefilled Google Form link, with `{election_id}`, `{field}`,
`{proposed_value}`, `{source}`, and similar placeholders), `contact_email`, and `preview` (turns
off downloads).

## License (proposed, to confirm before launch)

Data: Creative Commons Attribution 4.0 (`LICENSE-DATA.md`). Code: MIT (`LICENSE`).

## Citation (proposed)

See `CITATION.cff`.

This is an independent academic research project, not affiliated with or endorsed by the
National Labor Relations Board.
