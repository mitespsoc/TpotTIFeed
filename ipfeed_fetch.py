import json
import csv
import requests
import os

def writeToFile(data, headers, fileName):
    f = open(fileName, 'w', encoding='UTF8')
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(data)
    f.close()

searchUrl = "http://yourIP:yourPort/ipfeed/_search?size=10000&pretty=true"
headers = {
    'Content-Type': 'application/json',
}

hits = requests.get(searchUrl, headers=headers).json()['hits']['hits']
hitsArray = []
outFile = open('ipfeed.json', 'w')
for hit in hits:
    json.dump(hit['_source'], outFile)
    outFile.write("\n")

os.system('cmd /k "git add ipfeed.json"')
os.system('cmd /k "git commit -m "IP Feed Update"')
os.system('cmd /k "git push"')
