"""
Fills in the x and y columns of data/shrines.csv by clicking on the map
image (using plt.ginput).

Usage:
    pip install matplotlib pillow
    python mark_shrines.py

Put the map image (jpeg) in the data/ folder and change MAP_IMAGE below
if the file has a different name.

Controls (for each shrine):
    - left click          -> records the position and moves to the next shrine
    - Enter (no click)    -> skips this shrine (x and y stay empty)
    - closing the window  -> stops the script; progress is already saved
You can run the script again at any time: it only asks for the shrines
that still have no x, y.

Note: the coordinates are in image pixels (origin at the top-left corner,
y grows downwards). They can be converted to km later with a scale factor.
"""
import csv

import matplotlib.image as mpimg
import matplotlib.pyplot as plt

# ---- Settings -------------------------------------------------------------
MAP_IMAGE = "data/botw_map.jpg"   # path to the map image
CSV_FILE = "data/shrines.csv"     # file created by scrape_shrines.py
# ---------------------------------------------------------------------------


def load(path):
    """Reads the CSV and returns a list of dicts, one per shrine.
    Each dict has the keys: id, name, region, x, y."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(path, rows):
    """Writes all rows back to the CSV, keeping the same column order."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def main():
    rows = load(CSV_FILE)
    img = mpimg.imread(MAP_IMAGE)

    # Interactive mode: lets the window update while we wait for clicks
    plt.ion()
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.imshow(img)

    # Redraw the points that were already marked (when resuming a session),
    # so we can see the progress made so far
    for r in rows:
        if r["x"] and r["y"]:
            ax.plot(float(r["x"]), float(r["y"]), "r.", markersize=6)

    # Only the shrines that still have no coordinates need to be marked
    pending = [r for r in rows if not (r["x"] and r["y"])]
    print(f"{len(pending)} shrines left to mark.")

    for r in pending:
        # The title tells us which shrine to click on and how far we are
        ax.set_title(f'[{r["id"]}/{len(rows)}] {r["name"]}  ({r["region"]})\n'
                     f'Click on its location, or press Enter to skip')
        fig.canvas.draw_idle()

        # Also print it in the terminal, in case the title is hard to read
        print(f'-> {r["id"]}: {r["name"]} ({r["region"]})')

        # Wait for ONE click. timeout=0 means "wait forever".
        # Returns a list with the clicked point [(x, y)], or [] if the user
        # pressed Enter without clicking.
        try:
            points = plt.ginput(1, timeout=0)
        except Exception:
            break                        # window was closed -> stop

        if not points:
            continue                     # Enter pressed -> skip this shrine

        # Store the pixel coordinates (1 decimal is enough precision)
        x, y = points[0]
        r["x"], r["y"] = f"{x:.1f}", f"{y:.1f}"

        # Mark the point on the map and save right away, so that no
        # progress is lost if the script or the window is closed
        ax.plot(x, y, "r.", markersize=6)
        save(CSV_FILE, rows)

    # Final save and a short summary
    save(CSV_FILE, rows)
    done = sum(1 for r in rows if r["x"] and r["y"])
    print(f"Finished: {done}/{len(rows)} shrines have coordinates.")


if __name__ == "__main__":
    main()