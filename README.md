# web-languages-code

This repo holds the code, templates, and data associated with the
web-languages dataset.

## Theory



## Install dependencies:
**Note:** This project requires Python 3.

## Setup

Install dependencies:

```bash
make init
```

Download and extract ISO-639-3 tables:
```
make get-table
```

(Optional) Combine Wikipedia language files:
```
make combine-wikipedia
```

Generate language Markdown files:
```
make generate
```

Downloaded data files (e.g., ISO-639-3 tables) are excluded from version control via `.gitignore`.

## Makefile Targets

| Target             | Description                                      |
|--------------------|--------------------------------------------------|
| init               | Install Python dependencies                      |
| get-table          | Download and unzip ISO-639-3 tables              |
| combine-wikipedia  | Combine Wikipedia language CSVs                  |
| generate           | Generate Markdown files from data                |

## License

The code in this repo is licensed under the Apache 2.0 license.

The templates are licensed CC0.

Data files (*.tsv) from mOSCAR and Wikipedia are copyright by them.

