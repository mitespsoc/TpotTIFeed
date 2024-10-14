
cd /home/lakshan/TpotTIFeed

# Running the fetchFeed.py script
python3 fetchFeed.py

# Checking if ipfeed.json and ipFeed.csv were generated
if [ -f "ipfeed.json" ] && [ -f "ipFeed.csv" ]; then

    # Added the files to git
    git add ipfeed.json ipFeed.csv

    # Commiting the changes with a timestamp
    git commit -m "Auto-update: $(date '+%Y-%m-%d %H:%M:%S')"

    git push origin main
else
    echo "Files ipfeed.json or ipFeed.csv not found."
fi

