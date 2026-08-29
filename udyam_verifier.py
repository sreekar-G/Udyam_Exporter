"""
Udyam Autofill & Verifier v5
==============================
DOM path: #ctl00_ContentPlaceHolder1_tblprint > tbody > tr (1st)
  - 2nd table inside = enterprise details
  - 3rd table inside = classification history
"""

import time, os, re, sys, json, csv
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

HOME_URL      = "https://www.udyamregistration.gov.in/"
UDYAM_PATTERN = re.compile(r'^UDYAM-[A-Z]{2}-\d{2}-\d{7}$', re.IGNORECASE)

INVALID_KEYWORDS = [
    "invalid udyam", "no record found", "not found",
    "verification failed", "incorrect verification", "please enter valid"
]

# Label → JSON key
# Keys match exactly what parse_label_value_table() / parse_6th_table() produce.
FIELD_MAP = {
    "name_of_enterprise":    ["name of enterprise"],
    "date_of_incorporation": ["date of incorporation"],
    "major_activity":        ["major activity"],
    "social_category":       ["social category"],
    "date_of_commencement":  ["date of commencement of production/business",
                              "date of commencement of production",
                              "date of commencement of business",
                              "date of commencement"],
    "org_type":              ["type of organisation", "type of organization"],
    "nic_code":              ["nic 2 digit code", "nic code", "nic 2 digit",
                              "nic"],
    "state":                 ["state"],
    "district":              ["district"],
    "gender":                ["gender"],
    # From 6th table
    "date_of_incorporation": ["date of udyam registration",
                              "date of incorporation"],
    "dic":                   ["dic"],
    "msme_dfo":              ["msme_dfo", "msme-dfo", "msme dfo"],
}

# Column header keywords for classification table (3rd table)
CLASS_COL_MAP = {
    "classification_year": ["classification year", "year", "financial year"],
    "enterprise_type":     ["enterprise type", "type of enterprise", "msme type", "type"],
    "classification_date": ["classification date", "effective date", "date"],
}


# ── Driver ────────────────────────────────────────────────

def get_driver():
    opts = Options()
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=opts)
        print("✅ Chrome launched (webdriver-manager)")
        return driver
    except Exception:
        pass
    try:
        driver = webdriver.Chrome(options=opts)
        print("✅ Chrome launched (system chromedriver)")
        return driver
    except Exception as e:
        print(f"❌ Chrome failed: {e}")
        print("   Fix: pip3 install webdriver-manager")
        return None


# ── Navigation ────────────────────────────────────────────

def navigate_to_verify(driver):
    print("  🌐 Loading Udyam portal...")
    driver.get(HOME_URL)
    time.sleep(3)
    for menu_text in ["Print/Verify", "Print / Verify", "Verify"]:
        try:
            links = driver.find_elements(By.PARTIAL_LINK_TEXT, menu_text)
            if links:
                links[0].click()
                time.sleep(2)
                for sl in driver.find_elements(By.PARTIAL_LINK_TEXT, "Verify"):
                    if "verify" in sl.text.lower() and "print" not in sl.text.lower():
                        sl.click()
                        time.sleep(2)
                        break
                if is_verify_page(driver):
                    print("  ✅ Verify page loaded!")
                    return True
        except Exception:
            continue
    try:
        for link in driver.find_elements(By.TAG_NAME, "a"):
            href = (link.get_attribute("href") or "").lower()
            if "verify" in href and "udyam" in href:
                link.click()
                time.sleep(2)
                if is_verify_page(driver):
                    return True
    except Exception:
        pass
    return False


def is_verify_page(driver):
    try:
        page = driver.page_source.lower()
        return ("captcha" in page or "verification code" in page) \
               and "udyam" in page \
               and bool(driver.find_elements(By.CSS_SELECTOR, "input[type='text']"))
    except Exception:
        return False


def find_udyam_input(driver):
    for eid in ["ContentPlaceHolder1_txtUdyamNo", "txtUdyamNo",
                "ctl00_ContentPlaceHolder1_txtUdyamNo"]:
        try:
            el = driver.find_element(By.ID, eid)
            if el.is_displayed():
                return el
        except Exception:
            pass
    try:
        for inp in driver.find_elements(By.CSS_SELECTOR, "input[type='text']"):
            attrs = " ".join([
                inp.get_attribute("id") or "",
                inp.get_attribute("name") or "",
                inp.get_attribute("placeholder") or "",
            ]).lower()
            if "udyam" in attrs:
                return inp
    except Exception:
        pass
    try:
        for inp in driver.find_elements(By.CSS_SELECTOR, "input[type='text']"):
            if inp.is_displayed() and inp.is_enabled():
                return inp
    except Exception:
        pass
    return None


# ── Autofill ──────────────────────────────────────────────

def process_id(driver, udyam_id, idx, total):
    print(f"\n{'─'*55}")
    print(f"  [{idx}/{total}]  {udyam_id}")
    print(f"{'─'*55}")

    if not navigate_to_verify(driver):
        print("  ⚠️  Auto-navigation failed.")
        print("  👉 Manually open: Print/Verify → Verify Udyam Registration")
        input("     Press ENTER once the verify page is open: ")

    time.sleep(1)
    field = find_udyam_input(driver)

    if field:
        try:
            field.clear()
            time.sleep(0.2)
            for char in udyam_id:
                field.send_keys(char)
                time.sleep(0.02)
            print(f"  ✅ Auto-filled: {udyam_id}")
        except Exception as e:
            print(f"  ⚠️  Autofill error: {e} — type '{udyam_id}' manually.")
    else:
        print(f"  ⚠️  Input field not found — type '{udyam_id}' manually.")

    print()
    print("  👉 Solve the CAPTCHA in Chrome and click Verify.")
    input("  ⏎  Press ENTER here once the result page has loaded: ")

    return scrape_result(driver, udyam_id)


# ── Core scraper ──────────────────────────────────────────

# Span ID → field label for ALL tables (searched driver-wide)
ALL_SPAN_ID_MAP = {
    # Table 2 — enterprise details
    "ctl00_ContentPlaceHolder1_lblEnterpriseName":      "name of enterprise",
    "ctl00_ContentPlaceHolder1_lblOrganisationType":    "type of organisation",
    "ctl00_ContentPlaceHolder1_lblServices":            "major activity",
    "ctl00_ContentPlaceHolder1_lblGender":              "gender",
    "ctl00_ContentPlaceHolder1_lblsocialcat":           "social category",
    "ctl00_ContentPlaceHolder1_lbldateofincorporation": "date of incorporation",
    "ctl00_ContentPlaceHolder1_lbldateofcommencement":  "date of commencement of production/business",
    # Table 6 — address + reg date
    "ctl00_ContentPlaceHolder1_lblState":               "state",
    "ctl00_ContentPlaceHolder1_lblDistrict":            "district",
    "ctl00_ContentPlaceHolder1_lblNIC":                 "nic_code_raw",
    "ctl00_ContentPlaceHolder1_lblNICCode":             "nic_code_raw",
    "ctl00_ContentPlaceHolder1_lblnic":                 "nic_code_raw",
    "ctl00_ContentPlaceHolder1_lblgmdic":               "dic",
    "ctl00_ContentPlaceHolder1_lblMSMEDI":              "msme_dfo",
    "ctl00_ContentPlaceHolder1_lblACKNOWLEDGEMENT":    "date_of_udyam_reg",
}


def scrape_by_span_ids(driver):
    """
    Extract all known fields by span ID from the full page (driver-wide).
    Returns dict of {field_label: value}.
    """
    data = {}
    for span_id, label in ALL_SPAN_ID_MAP.items():
        try:
            el  = driver.find_element(By.ID, span_id)
            val = el.text.strip()
            if val:
                data[label] = val
        except Exception:
            pass
    return data


def parse_label_value_table(table_el):
    """
    Fallback label→value extraction from a table element.
    Used only for fields not covered by span IDs.
    Handles 4-cell rows: label | value | label | value
    """
    data = {}
    try:
        rows = table_el.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            n = len(cells)
            for i in range(0, n - 1, 2):
                label = cells[i].text.strip().lower().rstrip(":").strip()
                value = cells[i + 1].text.strip()
                if label and value and label not in data:
                    data[label] = value
    except Exception as e:
        print(f"    [parse_label_value_table] {e}")
    return data


def parse_classification_table(table_el):
    """
    Parse classification history table.
    Returns list of {classification_year, enterprise_type, classification_date}.
    """
    entries = []
    try:
        rows = table_el.find_elements(By.TAG_NAME, "tr")
        if not rows:
            return entries

        # Detect header row (th or first tr)
        header_cells = rows[0].find_elements(By.TAG_NAME, "th")
        if not header_cells:
            header_cells = rows[0].find_elements(By.TAG_NAME, "td")

        # Map column index → field key
        col_idx = {}
        for ci, cell in enumerate(header_cells):
            h = cell.text.strip().lower()
            for field_key, keywords in CLASS_COL_MAP.items():
                if any(kw in h for kw in keywords):
                    if field_key not in col_idx:   # first match wins
                        col_idx[field_key] = ci
                    break

        print(f"    Classification table columns: {col_idx}")

        # Parse data rows
        data_rows = rows[1:] if header_cells else rows
        for row in data_rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells:
                continue
            entry = {
                "classification_year": "",
                "enterprise_type":     "",
                "classification_date": "",
            }
            for field_key, ci in col_idx.items():
                if ci < len(cells):
                    entry[field_key] = cells[ci].text.strip()

            # Fallback: if no col_idx matched, try to extract from row text
            if not any(entry.values()):
                row_text = " ".join(c.text.strip() for c in cells)
                yr_m  = re.search(r'\b(20\d{2})\b', row_text)
                typ_m = re.search(r'\b(micro|small|medium)\b', row_text, re.IGNORECASE)
                dt_m  = re.search(
                    r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{2}-\d{2})\b', row_text)
                if yr_m or typ_m:
                    entry["classification_year"] = yr_m.group(1)  if yr_m  else ""
                    entry["enterprise_type"]     = typ_m.group(1).capitalize() if typ_m else ""
                    entry["classification_date"] = dt_m.group(1)  if dt_m  else ""

            if any(entry.values()):
                entries.append(entry)

    except Exception as e:
        print(f"    [parse_classification_table] {e}")

    return entries


def scrape_result(driver, udyam_id):
    result = {
        "udyam_id":              udyam_id,
        "name_of_enterprise":    "",
        "date_of_incorporation": "",
        "major_activity":        "",
        "social_category":       "",
        "date_of_commencement":  "",
        "org_type":              "",
        "nic_code":              "",
        "state":                 "",
        "district":              "",
        "gender":                "",
        "date_of_udyam_reg":     "",
        "dic":                   "",
        "msme_dfo":              "",
        "enterprise_type":       [],
        "vstatus":               "Verified",
        "scraped_at":            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        page_lower = driver.page_source.lower()
        if any(kw in page_lower for kw in INVALID_KEYWORDS):
            print("  ❌ Invalid registration number")
            result["vstatus"] = "Invalid"
            return result

        # ── Locate the outer print table ─────────────────
        # CSS: #ctl00_ContentPlaceHolder1_tblprint tbody tr (first row)
        outer_tables = driver.find_elements(
            By.CSS_SELECTOR,
            "#ctl00_ContentPlaceHolder1_tblprint > tbody > tr"
        )

        if not outer_tables:
            # fallback: try without tbody (some browsers omit it in DOM)
            outer_tables = driver.find_elements(
                By.CSS_SELECTOR,
                "#ctl00_ContentPlaceHolder1_tblprint tr"
            )

        if not outer_tables:
            print("  ⚠️  Outer table #ctl00_ContentPlaceHolder1_tblprint not found")
            print("       Falling back to full-page table scan...")
            return _fallback_scrape(driver, result)

        first_tr = outer_tables[0]
        print(f"  ✅ Found outer table, first <tr> located")

        # Get all nested tables inside the first tr
        nested_tables = first_tr.find_elements(By.TAG_NAME, "table")
        print(f"  📊 Nested tables found: {len(nested_tables)}")

        if len(nested_tables) < 2:
            print("  ⚠️  Less than 2 nested tables — falling back to full scan")
            return _fallback_scrape(driver, result)

        # ── Step 1: span ID extraction (driver-wide, most reliable) ────
        print(f"  🔍 Extracting fields by span ID...")
        span_data = scrape_by_span_ids(driver)
        print(f"     Span ID hits: {len(span_data)}")
        for k, v in span_data.items():
            print(f"       {k!r:45} → {v!r}")

        # Map span data → result fields
        span_to_field = {
            "name of enterprise":                          "name_of_enterprise",
            "type of organisation":                        "org_type",
            "major activity":                              "major_activity",
            "gender":                                      "gender",
            "social category":                             "social_category",
            "date of incorporation":                       "date_of_incorporation",
            "date of commencement of production/business": "date_of_commencement",
            "state":                                       "state",
            "district":                                    "district",
            "nic_code_raw":                                "nic_code",
            "dic":                                         "dic",
            "msme_dfo":                                    "msme_dfo",
            "date_of_udyam_reg":                           "date_of_udyam_reg",
        }
        for span_label, field_key in span_to_field.items():
            if span_data.get(span_label):
                result[field_key] = span_data[span_label]

        # ── Step 2: fallback label scan on 2nd table for anything still missing ─
        missing = [k for k in ["name_of_enterprise","org_type","major_activity",
                                "gender","social_category","date_of_incorporation",
                                "date_of_commencement"] if not result[k]]
        if missing:
            print(f"  🔍 Fallback label scan on 2nd table for: {missing}")
            details_table = nested_tables[1]
            details_data  = parse_label_value_table(details_table)
            for field_key, keywords in FIELD_MAP.items():
                if result[field_key]:
                    continue
                for kw in keywords:
                    match = next((v for k, v in details_data.items() if kw in k), None)
                    if match:
                        result[field_key] = match
                        break

        # ── 3rd table = classification history ───────────
        if len(nested_tables) >= 3:
            class_table = nested_tables[2]
            print(f"  🔍 Parsing 3rd table (classification history)...")
            entries = parse_classification_table(class_table)
            if entries:
                result["enterprise_type"] = entries
                print(f"     Found {len(entries)} classification record(s)")
            else:
                print(f"  ⚠️  Classification table found but no rows parsed")
        else:
            print(f"  ⚠️  3rd table not found (only {len(nested_tables)} tables in first tr)")

        # ── Step 3: fallback row scan on 6th table for DIC/MSME/reg date ─
        # (span IDs already handled state/district/NIC above)
        if len(nested_tables) >= 6 and not all([result["dic"],
                                                 result["msme_dfo"],
                                                 result["date_of_udyam_reg"]]):
            sixth_table = nested_tables[5]
            rows = sixth_table.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 2:
                    label = cells[0].text.strip().lower().rstrip(":")
                    value = cells[-1].text.strip()
                    if not label or not value:
                        continue
                    if "date of udyam" in label and not result["date_of_udyam_reg"]:
                        result["date_of_udyam_reg"] = value
                    elif label == "dic" and not result["dic"]:
                        result["dic"] = value
                    elif "msme" in label and not result["msme_dfo"]:
                        result["msme_dfo"] = value

        # ── Print summary ─────────────────────────────────
        print()
        print(f"  📋 Name              : {result['name_of_enterprise']    or '—'}")
        print(f"  📋 Date Incorporated : {result['date_of_incorporation'] or '—'}")
        print(f"  📋 Major Activity    : {result['major_activity']        or '—'}")
        print(f"  📋 Social Category   : {result['social_category']       or '—'}")
        print(f"  📋 Date Commenced    : {result['date_of_commencement']  or '—'}")
        print(f"  📋 Org Type          : {result['org_type']               or '—'}")
        print(f"  📋 NIC Code          : {result['nic_code']               or '—'}")
        print(f"  📋 State             : {result['state']                  or '—'}")
        print(f"  📋 District          : {result['district']               or '—'}")
        print(f"  📋 DIC               : {result['dic']                    or '—'}")
        print(f"  📋 MSME-DFO          : {result['msme_dfo']               or '—'}")
        print(f"  📋 Date Udyam Reg    : {result['date_of_udyam_reg']      or '—'}")
        if result["enterprise_type"]:
            print(f"  📋 Classification History:")
            for e in result["enterprise_type"]:
                print(f"       {e['classification_year']:10}  "
                      f"{e['enterprise_type']:8}  {e['classification_date']}")
        else:
            print(f"  📋 Classification History : —")

    except Exception as e:
        print(f"  ⚠️  Scrape error: {e}")
        result["vstatus"] = "Error"

    return result


def _fallback_scrape(driver, result):
    """Full-page table scan fallback when outer table ID not found."""
    print("  🔄 Running fallback full-page scrape...")
    try:
        all_tables = driver.find_elements(By.CSS_SELECTOR, "table")
        for table in all_tables:
            data = parse_label_value_table(table)
            for field_key, keywords in FIELD_MAP.items():
                if result[field_key]:
                    continue
                for kw in keywords:
                    match = next((v for k, v in data.items() if kw in k), None)
                    if match:
                        result[field_key] = match
                        break

        # Try to find classification table
        for table in all_tables:
            rows = table.find_elements(By.TAG_NAME, "tr")
            if not rows:
                continue
            header_text = " ".join(
                c.text.strip().lower()
                for c in (rows[0].find_elements(By.TAG_NAME, "th") or
                          rows[0].find_elements(By.TAG_NAME, "td"))
            )
            if any(kw in header_text for kw in
                   ["classification year", "enterprise type", "classification date"]):
                entries = parse_classification_table(table)
                if entries:
                    result["enterprise_type"] = entries
                    break
    except Exception as e:
        print(f"  ⚠️  Fallback error: {e}")
    return result


# ── File I/O ──────────────────────────────────────────────

def load_ids(path):
    ids = []
    try:
        if path.lower().endswith(".csv"):
            with open(path, newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    ids.append(list(row.values())[0].strip().upper())
        else:
            if not HAS_PANDAS:
                print("❌ pip3 install pandas openpyxl")
                return []
            df  = pd.read_excel(path, dtype=str)
            col = df.columns[0]
            for c in df.columns:
                if df[c].dropna().astype(str).str.upper().str.startswith("UDYAM-").any():
                    col = c
                    break
            ids = df[col].dropna().astype(str).str.strip().str.upper().tolist()
    except Exception as e:
        print(f"❌ Load error: {e}")
    return [i for i in ids if i]


def save_results(results, base_path):
    ts        = datetime.now().strftime("%Y%m%d_%H%M")
    json_path = f"{base_path}_verified_{ts}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 JSON → {json_path}")
    return json_path


# ── Main ──────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("   Udyam Autofill & Verifier v5")
    print("=" * 55)

    if not HAS_SELENIUM:
        print("❌ pip3 install selenium webdriver-manager")
        return

    input_file = sys.argv[1] if len(sys.argv) > 1 \
        else input("\n📂 Enter path to Excel/CSV: ").strip().strip("'\"")

    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        return

    ids = load_ids(input_file)
    if not ids:
        print("❌ No IDs found.")
        return

    valid_ids   = [i for i in ids if UDYAM_PATTERN.match(i)]
    invalid_fmt = [i for i in ids if not UDYAM_PATTERN.match(i)]
    print(f"\n📋 {len(ids)} total  →  {len(valid_ids)} valid, {len(invalid_fmt)} invalid format")

    # Save JSON output to a "json" subfolder next to the input file,
    # instead of dumping it alongside the input file itself.
    input_dir  = os.path.dirname(os.path.abspath(input_file)) or "."
    json_dir   = os.path.join(input_dir, "json_folder")
    os.makedirs(json_dir, exist_ok=True)
    base_name  = os.path.splitext(os.path.basename(input_file))[0]
    base_path  = os.path.join(json_dir, base_name)

    print("\n🌐 Launching Chrome...")
    driver = get_driver()
    if not driver:
        return

    results = [
        {
            "udyam_id": uid, "name_of_enterprise": "",
            "date_of_incorporation": "", "major_activity": "",
            "social_category": "", "date_of_commencement": "",
            "org_type": "", "nic_code": "", "state": "", "district": "",
            "gender": "", "date_of_udyam_reg": "", "dic": "", "msme_dfo": "",
            "enterprise_type": [],
            "vstatus": "Invalid Format",
            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        for uid in invalid_fmt
    ]

    try:
        for i, uid in enumerate(valid_ids, 1):
            res = process_id(driver, uid, i, len(valid_ids))
            results.append(res)
            save_results(results, base_path)

            if i < len(valid_ids):
                print()
                cont = input("  ▶  Press ENTER for next ID  (q = quit): ").strip().lower()
                if cont == "q":
                    print("  ⛔ Stopped.")
                    break

    except KeyboardInterrupt:
        print("\n⛔ Interrupted — saving progress...")
    finally:
        try:
            driver.quit()
        except Exception:
            pass

    json_path = save_results(results, base_path)
    print(f"\n✅ Done! {len(results)} records.")
    print(f"\n💡 Generate PDF:")
    print(f"   python3 udyam_pdf_report.py \"{json_path}\"")


if __name__ == "__main__":
    main()


# ── Debug helper — run this after result page loads ───────
def debug_dump_tables(driver):
    """
    Call this manually to dump exact structure of
    #ctl00_ContentPlaceHolder1_tblprint nested tables.
    Paste output here so we can fix field parsing.
    """
    print("\n" + "="*60)
    print("DEBUG: Dumping nested table structure")
    print("="*60)

    outer = driver.find_elements(
        By.CSS_SELECTOR,
        "#ctl00_ContentPlaceHolder1_tblprint > tbody > tr"
    )
    if not outer:
        outer = driver.find_elements(
            By.CSS_SELECTOR,
            "#ctl00_ContentPlaceHolder1_tblprint tr"
        )
    if not outer:
        print("❌ Outer table not found!")
        return

    first_tr     = outer[0]
    nested_tables = first_tr.find_elements(By.TAG_NAME, "table")
    print(f"Total nested tables in first <tr>: {len(nested_tables)}\n")

    for ti, table in enumerate(nested_tables):
        print(f"── TABLE {ti+1} {'─'*40}")
        rows = table.find_elements(By.TAG_NAME, "tr")
        for ri, row in enumerate(rows):
            cells = row.find_elements(By.TAG_NAME, "td") + \
                    row.find_elements(By.TAG_NAME, "th")
            cell_texts = [f"[{c.text.strip()!r}]" for c in cells]
            print(f"  row[{ri}] ({len(cells)} cells): {' | '.join(cell_texts)}")
        print()