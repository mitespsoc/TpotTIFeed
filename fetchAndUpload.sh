#!/usr/bin/python3
import requests
import json
import csv

searchUrl = "http://4.194.176.219:64298/ipfeed/_search?size=10000&pretty=true"
headers = {
	'Content-Type': 'application/json',
}
query = {
	"query":
		{"bool":
			{"must":[
				{"range":{"LastDate": {"gte": "now-1d"}}}
			]
		}
	}
}

hits = requests.post(searchUrl, json=query, headers=headers).json()['hits']['hits']
outFile = open('ipfeed.json', 'w')
for hit in hits:
	json.dump(hit['_source'], outFile)
	outFile.write("\n")
outFile.close()

headers = ["UUID","IP","Count","Sources","FirstDate","LastDate"]
jsonFile = open('ipfeed.json', 'r')
ipFeedCsv = open('ipFeed.csv', 'w')
csvWriter = csv.writer(ipFeedCsv)
csvWriter.writerow(headers)
for row in jsonFile:
	ipObj = json.loads(row)
	ipObjSrcs = ipObj['Sources'].replace(",", "-").replace(' ', "")
	csvRow = [ipObj['UUID'],ipObj['IP'],str(ipObj['Count']),str(ipObjSrcs),ipObj['FirstDate'],ipObj['LastDate']]            
	csvWriter.writerow(csvRow)
jsonFile.close()
ipFeedCsv.close()
