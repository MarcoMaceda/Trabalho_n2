"""
Extracts the list of the 120 Breath of the Wild shrines from Thonky.com
and saves it to data/shrines.csv (id, name, region, x, y).

The x and y columns are left empty: the page has NO coordinates.
Fill them in later (e.g. with plt.ginput() on top of the map image).

Usage:
    pip install requests beautifulsoup4
    python scrape_shrines.py
"""
import csv
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

URL = "https://www.thonky.com/zelda-breath-of-the-wild/shrine"
OUT = "data/shrines.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (academic project - 6.0002 problem set)"}

# "Oman Au Shrine: Magnesis Trial" -> ("Oman Au", "Magnesis Trial")
ITEM_RE = re.compile(r"^(.*?)\s+Shrine:\s*(.*)$")


def parse(html):
    """Returns a list of [name, region] for every shrine found in the page."""
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    for h3 in soup.find_all("h3"):
        title = h3.get_text(strip=True)
        if not title.endswith("Region Shrines"):
            continue
        region = title.replace(" Region Shrines", "")
        shrine_list = h3.find_next("ol")      # the list right after the heading
        if shrine_list is None:
            continue
        for li in shrine_list.find_all("li", recursive=False):
            a = li.find("a")
            if a is None:
                continue
            m = ITEM_RE.match(a.get_text(strip=True))
            if not m:
                continue
            rows.append([m.group(1), region])
    return rows


def main():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    rows = parse(resp.text)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "region", "x", "y"])
        for i, r in enumerate(rows, start=1):
            w.writerow([i] + r + ["", ""])

    print(f"{len(rows)} shrines saved to {OUT}")
    if len(rows) != 120:
        print("WARNING: shrine count is different from 120!", file=sys.stderr)


if __name__ == "__main__":
    main()