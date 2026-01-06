#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Loop from 2011 to 2025
for year in {2011..2025}
do
    echo "Generating summary for $year..."
    python plots/generate_yearly_summary.py --year $year
done

echo "All summaries generated."
