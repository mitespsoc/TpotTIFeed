date=$(date)

source .venv/bin/activate
python fetchFeed.py

git add ipFeed.csv ipfeed.json
git commit -m "Updated IP Feed - $date"
git push
