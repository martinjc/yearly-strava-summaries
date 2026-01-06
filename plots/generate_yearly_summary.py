import json
import argparse
import os
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright

def main():
    parser = argparse.ArgumentParser(description='Generate yearly Strava summary.')
    parser.add_argument('--year', type=int, required=True, help='Year to generate summary for')
    parser.add_argument('--data', type=str, default='data/activities.json', help='Path to activities.json')
    parser.add_argument('--output', type=str, default='plots/output', help='Output directory')
    args = parser.parse_args()

    year = args.year
    data_path = args.data
    output_dir = args.output

    if not os.path.exists(data_path):
        print(f"Error: Data file not found at {data_path}")
        sys.exit(1)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Loading data from {data_path}...")
    with open(data_path, 'r') as f:
        activities = json.load(f)

    # Filter for Year and Type 'Run'
    year_activities = []
    for activity in activities:
        if activity.get('type') == 'Run':
            # start_date_local format: '2025-01-05T06:20:35Z'
            start_date = activity.get('start_date_local')
            if start_date:
                try:
                    dt = datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%SZ')
                    if dt.year == year:
                        year_activities.append(activity)
                except ValueError:
                    print(f"Warning: Could not parse date {start_date}")
                    continue

    print(f"Found {len(year_activities)} runs for year {year}")

    if not year_activities:
        print("No activities found. Exiting.")
        return

    # User provided bounding box for Cardiff area
    # [[-3.32322, 51.38586], [-3.14065, 51.51634]] -> [[minLon, minLat], [maxLon, maxLat]]
    bbox = [[-3.32322, 51.38586], [-3.14065, 51.51634]]
    min_lon, min_lat = bbox[0]
    max_lon, max_lat = bbox[1]

    main_map_activities = []
    
    # Statistics variables
    total_dist_meters = 0
    max_dist_meters = 0
    total_seconds = 0
    
    # For runs per week (simple approx: count runs, divide by 52? Or count distinct weeks?)
    # Let's count distinct ISO weeks.
    weeks_active = set()

    for act in year_activities:
        dist = act.get('distance', 0) # meters
        moving_time = act.get('moving_time', 0) # seconds
        
        total_dist_meters += dist
        total_seconds += moving_time
        if dist > max_dist_meters:
            max_dist_meters = dist
            
        start_date = act.get('start_date_local')
        dt = datetime.strptime(start_date, '%Y-%m-%dT%H:%M:%SZ')
        year_week = dt.isocalendar()[:2] # (year, week_num)
        weeks_active.add(year_week)

        # Check filter for main map
        # start_latlng is [lat, lon]
        start_latlng = act.get('start_latlng')
        if start_latlng and len(start_latlng) == 2:
            lat, lon = start_latlng
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                main_map_activities.append(act)

    # Calculate stats
    total_runs = len(year_activities)
    total_dist_km = total_dist_meters / 1000.0
    max_dist_km = max_dist_meters / 1000.0
    avg_dist_km = (total_dist_km / total_runs) if total_runs > 0 else 0
    
    # Average runs per week over the whole year (52 weeks)? Or just active weeks?
    # User said "average number of runs per week". Usually means Total Runs / 52.
    runs_per_week = total_runs / 52.0
    
    # Avg Pace: usually expressed as min/km. 
    # Total Time / Total Distance
    avg_speed_mps = (total_dist_meters / total_seconds) if total_seconds > 0 else 0
    # Pace = 1 / speed (min/km = 16.666 / mps)
    # min/km = (seconds / meters) * (1000 / 60)
    if total_dist_meters > 0:
        avg_pace_decimal = (total_seconds / total_dist_meters) * (1000 / 60)
        pace_min = int(avg_pace_decimal)
        pace_sec = int((avg_pace_decimal - pace_min) * 60)
        avg_pace_str = f"{pace_min}:{pace_sec:02d} /km"
    else:
        avg_pace_str = "0:00 /km"

    stats = {
        "totalRuns": f"{total_runs}",
        "totalDistance": f"{total_dist_km:.1f} km",
        "maxDistance": f"{max_dist_km:.1f} km",
        "avgDistance": f"{avg_dist_km:.1f} km",
        "runsPerWeek": f"{runs_per_week:.1f}",
        "avgPace": avg_pace_str
    }

    print(f"Stats: {stats}")
    print(f"Runs in main map area: {len(main_map_activities)}")

    # Prepare data object for JS
    # We only need necessary fields to keep file size small
    def clean_activity(act):
        return {
            "summary_polyline": act.get("map", {}).get("summary_polyline"),
            "date": act.get("start_date_local")
        }

    data_for_js = {
        "year": year,
        "runs": [clean_activity(a) for a in year_activities],
        "mainMapRuns": [clean_activity(a) for a in main_map_activities],
        "stats": stats,
        "boundingBox": bbox
    }

    # Write data to a JS file that the HTML can load
    # Or we can just read it in Python and inject it. 
    # Let's write to plots/templates/data.js (but templates might be checked in?)
    # Better to write a temp file or just serve it? 
    # Simpler: Write 'plots/templates/data.js' and have the HTML load it.
    
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    data_js_path = os.path.join(template_dir, 'data.js')
    
    with open(data_js_path, 'w') as f:
        f.write(f"const STRAVA_DATA = {json.dumps(data_for_js)};")

    # Launch Playwright
    output_filename = f"yearly_summary_{year}.png"
    output_file_path = os.path.join(output_dir, output_filename)
    
    html_file = f"file://{os.path.abspath(os.path.join(template_dir, 'year_summary.html'))}"
    # We need to load the data.js in the HTML. I added <script src="data.js"> (implicitly relative) to HTML earlier?
    # I should check the HTML content. I added <script src="year_summary.js"></script>. I did NOT add data.js.
    # I should inject the data or add the script tag. 
    # Since I can't easily edit HTML dynamically and cleanly without soup, 
    # I will rely on the HTML having correct relative path OR I will inject key code.
    
    # Actually, simpler: I'll modify the HTML to load 'data.js' before 'year_summary.js'.
    # I will assume I need to update the HTML template or just rely on the script tag I will inject.
    
    print("Generating screenshot...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1800, 'height': 1300}) # Match CSS dimensions
        
        # Capture console messages
        page.on("console", lambda msg: print(f"Browser Console: {msg.text}"))
        page.on("pageerror", lambda err: print(f"Browser Error: {err}"))

        
        page.goto(html_file)
        
        # Wait for map to render (D3 is fast but just in case)
        page.wait_for_timeout(2000) 
        
        page.screenshot(path=output_file_path)
        browser.close()

    print(f"Saved summary to {output_file_path}")

if __name__ == "__main__":
    main()
