# Inputs

Team logos and colours, plus the rosters (which git ignores: `.gitignore`
keeps spreadsheets in this folder out of the repo, since they list the kids'
names and pronouns).

- `<team number>.png`: each team's logo, e.g. `26460.png`.
- `teams.csv`: each team's text colour and coach colour. This one *is*
  committed (it's the one CSV exception in `.gitignore`).

| Team | Name | Names | Coach label and pill |
| --- | --- | --- | --- |
| 26460 | Dinonuggets | navy `#13213d` | orange `#d9661c` |
| 21986 | Midnight Snackers | dark navy-purple `#1c1b3a` | purple `#6a4c93`, darker than the logo's so small text stays readable |

## Rosters

Give each row a team number and the script picks that team's logo and
colours, so one sheet can mix teams:

```csv
team,name,pronouns,role
26460,Robin,she/her,Student
21986,Taylor,they/them,Student
```

The header row is optional; without one the columns are read as team, name,
pronouns, role. Buttons are grouped by team on the page.

Run from `robotics-buttons/`:

```sh
python make_buttons.py inputs/additional-2026.csv --blanks 1
```

`--blanks N` adds N spares *per team*.

## 2026 runs

- First print: Dinonuggets 16 people + 2 spares, Midnight Snackers 12 + 6.
- Additional (October): 2 more per team, plus 1 spare each, on one sheet.
