# Udyam Registration — Verification & Reporting Toolkit

This toolkit takes a list of Udyam Registration numbers, verifies each one
against the official government portal, and produces a professional PDF +
Excel report from the results.

It's a two-step pipeline:

```
 ids.xlsx  ──▶  udyam_verifier.py  ──▶  json/ids_verified_*.json  ──▶  udyam_pdf_report.py  ──▶  PDF + Excel report
(your list)      (browser automation,        (raw results)              (formatted report)
                   manual CAPTCHA solve)
```

---

## 1. What each script does

### `udyam_verifier.py`
- Reads a list of Udyam IDs from an `.xlsx` or `.csv` file.
- Opens Chrome, navigates to the official Udyam "Verify" page for each ID.
- **You solve the CAPTCHA manually** in the browser window and press Enter
  in the terminal to continue — this cannot be automated.
- Scrapes the verified enterprise details (name, incorporation date,
  classification history, etc.) from the result page.
- Saves everything to a JSON file in a `json/` subfolder next to your input
  file, after **every** ID (so progress isn't lost if you stop partway).

### `udyam_pdf_report.py`
- Reads the JSON file produced above.
- Generates a formatted **PDF report** (cover page, per-enterprise details,
  classification history summary).
- Generates a matching **Excel workbook** (`Enterprise Details` +
  `Classification History` sheets) alongside the PDF.

---

## 2. Requirements

### Python packages

```bash
pip install selenium webdriver-manager pandas openpyxl reportlab
```

| Package | Used by | Purpose |
|---|---|---|
| `selenium` | verifier | Browser automation |
| `webdriver-manager` | verifier | Auto-downloads the matching ChromeDriver |
| `pandas` | verifier | Reads the input `.xlsx`/`.csv` |
| `openpyxl` | both | Excel engine for `pandas` and for writing the report `.xlsx` |
| `reportlab` | report | Builds the PDF |

### Other requirements

- **Google Chrome** must be installed on your machine (`webdriver-manager`
  only downloads the driver, not the browser itself).
- This is designed for **interactive, local use** — it opens a visible
  Chrome window and pauses for you to solve CAPTCHAs and press Enter. It is
  **not** meant to run unattended on a headless server.

---

## 3. Folder structure

```
your-folder/
├── ids.xlsx                          ← your input list of Udyam IDs
├── json/                             ← auto-created by udyam_verifier.py
│   └── ids_verified_20260829_1400.json
├── ids_verified_20260829_1400_report_20260829_1405.pdf
└── ids_verified_20260829_1400_report_20260829_1405.xlsx
```

The `json/` subfolder is created automatically the first time you run the
verifier — you don't need to make it yourself.

---

## 4. Step-by-step usage

### Step 1 — Prepare your input file
Create an `.xlsx` or `.csv` with a column of Udyam IDs, e.g.:

```
UDYAM-KA-01-0000001
UDYAM-MH-02-0001234
```

IDs must match the format `UDYAM-XX-NN-NNNNNNN`. Rows that don't match this
pattern are still included in the final output, marked as `Invalid Format`.

### Step 2 — Run the verifier

```bash
python udyam_verifier.py "C:\path\to\ids.xlsx"
```

or just run it with no argument and paste the path when prompted:

```bash
python udyam_verifier.py
```

For each ID:
1. Chrome opens and the ID is auto-typed into the Udyam Verify page.
2. **Solve the CAPTCHA yourself** and click Verify in the browser.
3. Press **Enter** in the terminal once the result page has loaded.
4. Press Enter again to move to the next ID, or type `q` to stop early.

Progress is saved after every ID to `json/<yourfile>_verified_<timestamp>.json`.
At the end, the script prints the exact command to run Step 3 with that file.

### Step 3 — Generate the report

```bash
python udyam_pdf_report.py "C:\path\to\ids\json\ids_verified_20260829_1400.json"
```

This produces both a `.pdf` and a `.xlsx` file next to the JSON file, with
matching timestamps in the filename.

---

## 5. Troubleshooting

**"openpyxl not installed" / Excel file never appears**
Run `pip install openpyxl`. The report script now raises a clear error if
this dependency is missing, instead of silently skipping the Excel file.

**`JSONDecodeError: Expecting value: line 1 column 1 (char 0)`**
Usually means the JSON file is either empty or has a Windows-added BOM
(e.g. from being re-saved in Notepad). The report script now reads with
`utf-8-sig`, which handles a BOM automatically, and gives a clearer error
message for a genuinely empty or corrupt file.

**Chrome fails to launch**
Make sure Google Chrome is installed and up to date. If
`webdriver-manager` fails to download a driver (e.g. no internet access,
or a corporate proxy), it falls back to your system's installed
`chromedriver` — make sure one is on your `PATH` in that case.

**Auto-navigation to the Verify page fails**
The script tries to click through the site menu automatically, but the
Udyam portal's layout can change. If it fails, it will pause and ask you
to manually navigate to **Print/Verify → Verify Udyam Registration**, then
press Enter to continue.

**Paths with spaces or copied from Windows Explorer**
Wrap paths in quotes on the command line. Both scripts also strip stray
leading/trailing quotes automatically, so pasting a path copied via
"Copy as path" in Windows Explorer works as-is.

---

## 6. Output fields

Each record in the JSON / report includes:

`udyam_id`, `name_of_enterprise`, `date_of_incorporation`, `major_activity`,
`social_category`, `date_of_commencement`, `org_type`, `nic_code`, `state`,
`district`, `gender`, `date_of_udyam_reg`, `dic`, `msme_dfo`,
`enterprise_type` (classification history: year, type, date), `vstatus`
(`Verified` / `Invalid` / `Invalid Format` / `Error` / `Timeout`), and
`scraped_at` (timestamp).