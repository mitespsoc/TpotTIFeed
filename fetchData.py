
import requests
import json
import csv
import pandas as p
import time
from datetime import datetime

# Write data into CSV
def writeToFile(data, headers, fileName):
        f = open(fileName, 'w', encoding='UTF8')
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(data)
        f.close()

# Queries to fetch data from each honey pot
queryTime = "now-1h"
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

# Add Hits Data to Elastic
def addToElastic(data, honeyPot):
	now = datetime.now()
	date = now.strftime("%m/%d/%Y -- %H%M:%S")
	searchUrl = "http://localhost:64298/ipfeed/_search?&pretty=true"
	insertUrl = "http://localhost:64298/ipfeed/_doc/?pretty"
	headers = {'Content-Type': 'application/json'}
	for obj in data:
		searchQuery = {
                	"query": {
                        	"bool": {
                                	"must": [
                                        	{"match": {"IP": obj[0]}},
                                	]
                        	}
                	}
        	}
		insertQuery = {
                	"IP": obj[0],
                	"Count": obj[1],
	                "Source": honeyPot,
	                "FirstDate": date,
        	        "LastDate": date,
        	}
		response = requests.post(searchUrl, json=searchQuery, headers=headers).json()['hits']['hits']
		if response != []:
			id = response[0]['_id']
			firstDate = response[0]['_source']['FirstDate']
			count = response[0]['_source']['Count']
			updateUrl = "http://localhost:64298/ipfeed/_doc/" + id + "?pretty"
			updateQuery = insertQuery = {
                        	"IP": obj[0],
                	        "Count": int(obj[1])+int(count),
        	                "Source": honeyPot,
	                        "FirstDate": firstDate,
                        	"LastDate": date,
                	}
			response = requests.post(updateUrl, json=updateQuery, headers=headers).json()
			print("[+] indexID: " + response['_id'] + " result: " + response['result'])
		else:
			response = requests.post(insertUrl, json=insertQuery, headers=headers).json()
			print("[+] indexID: " + response['_id'] + " result: " + response['result'])

# Get IP hit count
def getHitCount(hitsArray):
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
	return data

# Functions to store fetched data into CSV files
def getTannerData(hitsArray):
	hitsData = getHitCount(hitsArray)
	addToElastic(hitsData, "Tanner")

def getMailoneyData(hitsArray):
	headers = ["IP","Data"]
	data = []
	for hit in hitsArray:
		dataObj = [hit["_source"]["src_ip"],hit["_source"]["data"]]
		data.append(dataObj)
	writeToFile(data, headers, "MailoneyData.csv")
	hitsData = getHitCount(hitsArray)
	addToElastic(hitsData, "Mailoney")

def getCowrieData(hitsArray):
	headers = ["IP","Reputation","Username","Password","Message","CowrieEventId"]
	data = []
	for hit in hitsArray:
		dataObj = [hit["_source"]["src_ip"],hit["_source"]["ip_rep"],hit["_source"]["username"],hit["_source"]["password"],hit["_source"]["message"],hit["_source"]["eventid"]]
		data.append(dataObj)
	writeToFile(data, headers, "CowrieData.csv")
	hitsData = getHitCount(hitsArray)
	addToElastic(hitsData, "Cowrie")

def getSuricataData(hitsArray):
	hitsData = getHitCount(hitsArray)
	addToElastic(hitsData, "Suricata")

def execute():
	honeyPots = [
	        {'function': getTannerData, 'query': tannerDataQuery},
        	{'function': getMailoneyData, 'query': mailoneyDataQuery},
	        {'function': getCowrieData, 'query': cowrieDataQuery},
		{'function': getSuricataData, 'query': suricataDataQuery}
        ]
	headers = {
		'Content-Type': 'application/json',
	}
	url = "http://localhost:64298/*/_search?size=10000&pretty=true"
	for pot in honeyPots:
		hits = requests.post(url, json=pot['query'], headers=headers).json()['hits']['hits']
		pot['function'](hits)
	date = datetime.now()
	
execute()
