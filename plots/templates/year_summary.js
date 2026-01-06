// Expects data to be available via a global variable or fetch
// For this setup, we will likely inject it or fetch it. 
// Let's assume a global object 'STRAVA_DATA' containing { year: 2025, runs: [...], mainMapRuns: [...], stats: {...} }

// Wait for data definition if injected directly in script tag before this
document.addEventListener("DOMContentLoaded", function () {
    if (typeof STRAVA_DATA === 'undefined') {
        console.error("STRAVA_DATA not found. Please ensure data is loaded.");
        return;
    }

    const { year, runs, mainMapRuns, stats, boundingBox } = STRAVA_DATA;

    // 1. Set Title and Stats
    document.getElementById('year-title').innerText = year;
    document.getElementById('total-runs').innerText = stats.totalRuns;
    document.getElementById('total-distance').innerText = stats.totalDistance;
    document.getElementById('max-distance').innerText = stats.maxDistance;
    document.getElementById('avg-distance').innerText = stats.avgDistance;
    document.getElementById('runs-per-week').innerText = stats.runsPerWeek;
    document.getElementById('avg-pace').innerText = stats.avgPace;

    // 2. Render Left Panel Grid
    drawGrid(runs);

    // 3. Render Right Panel Main Map
    drawMainMap(mainMapRuns, boundingBox);

});

function drawGrid(runs) {
    const container = document.getElementById('left-panel');
    const width = container.clientWidth;
    const height = container.clientHeight;

    // Calculate grid dimensions
    // We want to fill the space. 
    // Area = w * h. Area per run = Area / n_runs. Side = sqrt(Area/n).
    // Let's approximate a square grid relative to aspect ratio
    const n = runs.length;
    const aspectRatio = width / height;

    // cols * rows >= n
    // cols / rows ~ aspectRatio  => cols ~ rows * ar
    // rows * rows * ar >= n => rows >= sqrt(n / ar)

    const rows = Math.ceil(Math.sqrt(n / aspectRatio));
    const cols = Math.ceil(n / rows);

    const cellWidth = width / cols;
    const cellHeight = height / rows;

    // Use the smaller dimension to keep aspect ratio of runs somewhat sane? 
    // Actually, distinct runs have different bounding boxes. 
    // We should project each run into a square/box of cellWidth x cellHeight.

    const svg = d3.select("#left-panel")
        .append("svg")
        .attr("width", width)
        .attr("height", height);

    runs.sort((a, b) => new Date(a.date) - new Date(b.date)); // Sort by date

    runs.forEach((run, i) => {
        const r = Math.floor(i / cols);
        const c = i % cols;

        const xVal = c * cellWidth;
        const yVal = r * cellHeight;

        // Group for this cell
        const g = svg.append("g")
            .attr("transform", `translate(${xVal}, ${yVal})`);

        // Decode polyline to coordinates
        const coordinates = polyline.decode(run.summary_polyline);
        // GeoJSON expects [lon, lat], polyline decodes to [lat, lon]
        const geoJsonCoords = coordinates.map(pt => [pt[1], pt[0]]);

        const feature = {
            type: "Feature",
            geometry: {
                type: "LineString",
                coordinates: geoJsonCoords
            }
        };

        // Create a projection for just this run to fit in the cell
        // We add some padding
        const padding = 5;
        const fitWidth = cellWidth - 2 * padding;
        const fitHeight = cellHeight - 2 * padding;

        const projection = d3.geoMercator()
            .fitSize([fitWidth, fitHeight], feature);

        const pathGenerator = d3.geoPath().projection(projection);

        g.append("path")
            .datum(feature)
            .attr("d", pathGenerator)
            .attr("transform", `translate(${padding}, ${padding})`)
            .attr("class", "run-path")
            .style("stroke-width", "1.5px");
    });
}

function drawMainMap(runs, boundingBox) {
    const container = document.getElementById('right-panel');
    const width = container.clientWidth;
    const height = container.clientHeight;

    const svg = d3.select("#right-panel")
        .append("svg")
        .attr("width", width)
        .attr("height", height);

    // Bounding Box: [[-3.32322, 51.38586], [-3.14065, 51.51634]] -> [[minLon, minLat], [maxLon, maxLat]]
    // D3 fitExtent expects [[x0, y0], [x1, y1]] which corresponds to pixels usually?
    // Actually d3.geoMercator().fitBounds is not standard in v7 basic, verify.
    // .fitSize fits a GeoJSON object. We can create a Polygon for the bounding box.

    // bounding box is [[minLon, minLat], [maxLon, maxLat]] but user provided [[-3.32322, 51.38586], [-3.14065, 51.51634]]
    // Left Lon: -3.32322 (West), Bottom Lat: 51.38586 (South)
    // Right Lon: -3.14065 (East), Top Lat: 51.51634 (North)

    // Let's call them minLon, minLat, maxLon, maxLat
    // Note: user input format [[-3.32322, 51.38586], [-3.14065, 51.51634]]
    // Let's update generate script to pass this clearly.

    const minLon = boundingBox[0][0];
    const minLat = boundingBox[0][1];
    const maxLon = boundingBox[1][0];
    const maxLat = boundingBox[1][1];

    const bboxFeature = {
        type: "Feature",
        geometry: {
            type: "Polygon",
            coordinates: [[
                [minLon, minLat],
                [minLon, maxLat],
                [maxLon, maxLat],
                [maxLon, minLat],
                [minLon, minLat]
            ]]
        }
    };

    const geometry = bboxFeature.geometry;

    // Use fitExtent with some padding to ensure it feels "full" but safe
    const projection = d3.geoMercator()
        .fitExtent([[20, 20], [width - 20, height - 20]], geometry);

    const pathGenerator = d3.geoPath().projection(projection);

    // Optional: Draw bounding box for debug?
    // svg.append("path").datum(bboxFeature).attr("d", pathGenerator).style("stroke", "black").style("fill", "none");

    runs.forEach(run => {
        const coordinates = polyline.decode(run.summary_polyline);
        const geoJsonCoords = coordinates.map(pt => [pt[1], pt[0]]);

        const feature = {
            type: "Feature",
            geometry: {
                type: "LineString",
                coordinates: geoJsonCoords
            }
        };

        svg.append("path")
            .datum(feature)
            .attr("d", pathGenerator)
            .attr("class", "main-map-path");
    });
}

// Polyline decoder utility (simple version or from external lib)
// Since we can't easily import npm modules in this simple file unless we bundle, 
// I'll include a simple decode function.
// Source: https://github.com/mapbox/polyline/blob/master/src/polyline.js

var polyline = {};

polyline.decode = function (str, precision) {
    var index = 0,
        lat = 0,
        lng = 0,
        coordinates = [],
        shift = 0,
        result = 0,
        byte = null,
        latitude_change,
        longitude_change,
        factor = Math.pow(10, precision || 5);

    // Coordinates have variable length when encoded, so just keep
    // track of whether we've hit the end of the string. In each
    // loop iteration, a single coordinate is read.
    while (index < str.length) {

        // Reset shift, result, and byte
        byte = null;
        shift = 0;
        result = 0;

        do {
            byte = str.charCodeAt(index++) - 63;
            result |= (byte & 0x1f) << shift;
            shift += 5;
        } while (byte >= 0x20);

        latitude_change = ((result & 1) ? ~(result >> 1) : (result >> 1));

        shift = result = 0;

        do {
            byte = str.charCodeAt(index++) - 63;
            result |= (byte & 0x1f) << shift;
            shift += 5;
        } while (byte >= 0x20);

        longitude_change = ((result & 1) ? ~(result >> 1) : (result >> 1));

        lat += latitude_change;
        lng += longitude_change;

        coordinates.push([lat / factor, lng / factor]);
    }

    return coordinates;
};
