# Union elections before the NLRB, 1936 to 1960

A research dataset of {{n_elections}} union representation elections held under the National Labor Relations Act, rebuilt from the Board's published decisions. For each election it records where it took place, the employer's industry, the union, and what is known of the result, with a source for each value.

<div data-component="kpis"></div>

<div data-component="year-chart"></div>

## What each record contains

- **Where.** The county and state of the plant, with a FIPS code, the passage the location was read from, and an evidence tier.
- **Industry.** The employer's business, coded to the 1987 Standard Industrial Classification.
- **Union.** The petitioning union and its affiliation (AFL, CIO, or independent), the type of election, and the size of the bargaining unit when the decision states it.
- **Result.** The outcome and, where found, the vote tally, each with its source document.
- **Case.** The NLRB case number, citation, and decision date, with a link to the decision.

## Read this before using the data

- **Results are incomplete.** {{pct_definite}} of records have a definite result. For {{n_directed}} records the Board ordered an election, but the result is in a later document we have not found yet. Do not compute union win rates from this release: the known results lean toward wins.
- **This is not every NLRB election.** The dataset covers the elections in the source lists and in published Board decisions. Many elections held by agreement of the parties never produced a published decision.
- **"Do." rows count.** {{n_ditto}} rows are marked "Do." (ditto) in the source lists, meaning the same employer as the row above, often on a different date. They are separate entries and are kept.
- **Pilot years are partial.** 1950, 1955, and 1960 test the method on later years. They hold far fewer elections than were held in those years.

<div data-component="start"></div>

## How to cite (proposed)

<div data-component="cite"></div>

## Who made this

Matthew S. Johnson and Uriel Galace, with research assistants <span class="todo">names to confirm</span>. Questions and corrections are welcome on the [Contribute](#contribute) page.
