
cd /home/lakshan/TpotTIFeed

# Running fetchFeed.py to generate ipfeed.json and ipFeed.csv
python3 fetchFeed.py

# Added the files to the git repository
git add ipfeed.json ipFeed.csv


git commit -m "Automated update of ipfeed files"


git push origin main
