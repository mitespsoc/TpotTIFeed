import requests
import json
import csv
import pandas as p

# Write data into CSV
def writeToFile(data, headers, fileName):
        f = open(fileName, 'w', encoding='UTF8')
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
        f.close()

# Queries to fetch data from each honey pot
tannerDataQuery = {
   "query": {
      "bool": {
        "must": [
          {"match": {"type": "Tanner"}}, 
          {"range": {"@timestamp": { "gte": "now-1h"}}}
        ]
      }
   }
}

mailoneyDataQuery = {
   "query": {
      "bool": {
        "must": [
          {"match": {"type": "Mailoney"}},
          {"range": {"@timestamp": { "gte": "now-1h"}}}
        ]
      }
   }
}

cowrieDataQuery = {
   "query": {
      "bool": {
        "must": [
          {"match": {"type": "Cowrie"}},
          {"exists": {"field": "username"}},
          {"exists": {"field": "ip_rep"}},
          {"range": {"@timestamp": { "gte": "now-1h"}}}
        ]
      }
   }
}

suricataDataQuery = {
  "query": {
    "bool": {
      "must": [
        {"match": {"type": "Suricata"}},
        {"match": {"event_type": "alert"}},
        {"range": {"@timestamp": {"gte": "now-10m"}}}
      ]
    }
  }
}

# Functions to store fetched data into CSV files
def getTannerData(hitsArray):
	headers = ["IP","HitCount"]
	ipObjList = []
	ipList = []
	data = []
	for obj in hitsArray:
		IP = obj["_source"]["src_ip"]
		ipList.append(IP)

	ipSet = set(ipList)
	for ip in ipSet:
		count = 0
		for i in ipList:
			if (ip == i):
				count+=1
		ipObj = {"ip": ip, "count": count}
		ipObjList.append(ipObj)

	for ipObj in ipObjList:
		dataObj = [ipObj['ip'], ipObj['count']]
		data.append(dataObj)
	writeToFile(data, headers, "TannerData.csv")

def getMailoneyData(hitsArray):
	headers = ["IP","Data"]
	data = []
	for hit in hitsArray:
		dataObj = [hit["_source"]["src_ip"],hit["_source"]["data"]]
		data.append(dataObj)
	writeToFile(data, headers, "MailoneyData.csv")

def getCowrieData(hitsArray):
	headers = ["IP","Reputation","Username","Password","Message","CowrieEventId"]
	data = []
	for hit in hitsArray:
		dataObj = [hit["_source"]["src_ip"],hit["_source"]["ip_rep"],hit["_source"]["username"],hit["_source"]["password"],hit["_source"]["message"],hit["_source"]["eventid"]]
		data.append(dataObj)
	writeToFile(data, headers, "CowrieData.csv")

def execute():
	honeyPots = [
	        {'function': getTannerData, 'query': tannerDataQuery},
        	{'function': getMailoneyData, 'query': mailoneyDataQuery},
	        {'function': getCowrieData, 'query': cowrieDataQuery}
        ]
	headers = {
		'Content-Type': 'application/json',
	}
	url = "http://localhost:64298/*/_search?size=10000&pretty=true"
	for pot in honeyPots:
		hits = requests.post(url, json=pot['query'], headers=headers).json()['hits']['hits']
		pot['function'](hits)

execute()
