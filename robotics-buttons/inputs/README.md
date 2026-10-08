# Inputs

Team logos and the settings used for each team's buttons. Put the roster CSVs
here too: `.gitignore` keeps spreadsheets in this folder out of git, since
they list the kids' names and pronouns.

Run these from `robotics-buttons/`.

## Dinonuggets 26460 (2026)

Navy names and orange coach labels, picked from the logo. Roster: 16 people
(both Johns, both Lauras), plus 2 blank spares to fill the last page.

```sh
python make_buttons.py inputs/dinonuggets-26460.csv \
    --logo inputs/dinonuggets-26460-logo.webp \
    --color "#13213d" --coach-color "#d9661c" --blanks 2 \
    --out out/dinonuggets-26460
```

## Midnight Snackers 21986 (2026)

Dark navy-purple names and purple coach labels (darker than the logo's purple
so small text stays readable). Roster: 12 people, plus 6 blank spares.

```sh
python make_buttons.py inputs/midnight-snackers-21986.csv \
    --logo inputs/midnight-snackers-21986-logo.webp \
    --color "#1c1b3a" --coach-color "#6a4c93" --blanks 6 \
    --out out/midnight-snackers-21986
```
