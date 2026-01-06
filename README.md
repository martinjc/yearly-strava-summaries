# Yearly Strava Summaries

This project generates visual yearly summaries of your Strava running activities. It creates high-resolution images suitable for printing (18cm x 13cm landscape), featuring a grid of every run's shape, a map of runs in a specific area (Cardiff), and summary statistics.

## Project Structure

-   `data/activities.json`: Strava activities data (JSON format).
-   `plots/generate_yearly_summary.py`: Main Python script to generate the visualization.
-   `plots/templates/`: Contains the HTML, CSS, and JS templates for the visualization.
    -   `year_summary.html`: Layout structure.
    -   `year_summary.css`: Styling (print size, colors, fonts).
    -   `year_summary.js`: D3.js logic for rendering maps.
-   `generate_all_years.sh`: Shell script to batch generate summaries for 2011-2025.
-   `plots/output/`: Directory where generated images are saved.

## Prerequisites

-   Python 3
-   Google Chrome / Chromium (managed by Playwright)

## Setup

1.  **Activate the virtual environment**:
    ```bash
    source venv/bin/activate
    ```

2.  **Install dependencies** (if not already installed):
    The project relies on `playwright`, `pandas`, `stravalib`, `python-dotenv`.
    Ensure Playwright browsers are installed:
    ```bash
    playwright install chromium
    ```

## Usage

### Generate a Single Year
To generate a visualization for a specific year (e.g., 2025):

```bash
python plots/generate_yearly_summary.py --year 2025
```

The output image will be saved to `plots/output/yearly_summary_2025.png`.

### Generate All Years
To generate summaries for all years from 2011 to 2025:

```bash
./generate_all_years.sh
```

## Customization

-   **Styles**: Edit `plots/templates/year_summary.css` to change colors, fonts, or dimensions.
-   **Layout**: Edit `plots/templates/year_summary.html` to modify the DOM structure.
-   **Map Logic**: Edit `plots/templates/year_summary.js` to change D3 projection settings or map rendering logic.
-   **Bounding Box**: The "Main Map" is currently hardcoded to the Cardiff area in `plots/generate_yearly_summary.py` (and `plots/templates/year_summary.js` logic expects coordinates). To change this, update the `bbox` variable in the Python script.
