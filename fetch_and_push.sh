cd ~/TpotTIFeed


python3 fetchFeed.py


if [ -f "ipfeed.json" ] && [ -f "ipFeed.csv" ]; then
    # Added the files to Git
    git add ipfeed.json ipFeed.csv
    
   
    git commit -m "Update IP feed"

    git push origin main  
else
    echo "Files not found!"
fi

