import requests
import json
import csv
from datetime import datetime
from ipaddress import ip_address
#curl -XPUT "http://localhost:64298/ipfeed?pretty" 
#-d '{"settings": {"number_of_shards": 1}},{"mappings": {"_default": {"_timestamp": {"enabled": true, "store": true, "format": "basic_date_time"}}}}'
#-H 'Content-Type: application/json'

# Write data into CSV
def writeToFile(data, headers, fileName):
	f = open(fileName, 'w', encoding='UTF8')
	writer = csv.writer(f)
	writer.writerow(headers)
	writer.writerows(data)
	f.close()

# Get IP hit count
def getHitCount(hitsArray):
	ipObjList = []
	ipList = []
	data = []
	for obj in hitsArray:
		IP = obj["_source"]["src_ip"]
		if ip_address(IP).is_global:
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

# Delete old IP from Elastic
def deleteFromElastic():
	searchUrl = "http://localhost:64298/ipfeed/_search?&pretty=true"
	headers = {'Content-Type': 'application/json'}
	searchQuery = {
                "query":
                        {"bool":
                                {"must":
                                        [
                                                {"range":
                                                        {"LastDate": {"lt": "now-14d"}}
                                                }
                                        ]
                                }
                        }
                }
	hits = requests.post(searchUrl, json=searchQuery, headers=headers).json()['hits']['hits']
	if len(hits) > 0:
		print("[+] Deleting " + len(hits) + " documents...")
		for hit in hits:
			deleteUrl = 'http://localhost:64298/ipfeed/_doc/' + hit["_id"] + '?pretty'
			response = requests.delete(deleteUrl)
			print("[+] indexID: " + hit["_id"] + " result: " + response["result"])
	else:
		print("[+] No old IPs")
	return len(hits)
# Add Hits Data to Elastic
def addToElastic(data, honeyPot):
	now = datetime.now()
	date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
	searchUrl = "http://localhost:64298/ipfeed/_search?&pretty=true"
	insertUrl = "http://localhost:64298/ipfeed/_doc/?pretty"
	headers = {'Content-Type': 'application/json'}
	created = 0
	updated = 0
	failed = 0
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
			"Sources": honeyPot,
			"FirstDate": date,
			"LastDate": date,
		}
		response = requests.post(searchUrl, json=searchQuery, headers=headers).json()['hits']['hits']
		
		if response != []:
			id = response[0]['_id']
			firstDate = response[0]['_source']['FirstDate']
			sources = response[0]['_source']['Sources']
			count = response[0]['_source']['Count']
			updateUrl = "http://localhost:64298/ipfeed/_doc/" + id + "?pretty"
			if sources.find(honeyPot) == -1:
				updateQuery = insertQuery = {
        	       		        "IP": obj[0],
                		        "Count": int(obj[1])+int(count),
                       		        "Sources": sources + ", " + honeyPot,
                               		"FirstDate": firstDate,
					"LastDate": date,
				}
				response = requests.post(updateUrl, json=updateQuery, headers=headers).json()
				if response['result'] != 'updated':
					failed+=1
				else:
					updated+=1
				print("[+] indexID: " + response['_id'] + " result: " + response['result'])
			else:
				updateQuery = insertQuery = {
					"IP": obj[0],
					"Count": int(obj[1])+int(count),
					"Sources": sources,
					"FirstDate": firstDate,
					"LastDate": date
				}
				response = requests.post(updateUrl, json=updateQuery, headers=headers).json()
				if response['result'] != 'updated':
					failed+=1
				else:
					updated+=1
				print("[+] indexID: " + response['_id'] + " result: " + response['result'])
		else:
			response = requests.post(insertUrl, json=insertQuery, headers=headers).json()
			if response['result'] != 'created':
				failed+=1
			else:
				created+=1
			print("[+] indexID: " + response['_id'] + " result: " + response['result'])
	return created, updated, failed

# Queries to fetch data from each honey pot
tannerDataQuery = {
   "query": {
      "bool": {
        "must": [
          {"match": {"type": "Tanner"}}, 
          {"range": {"@timestamp": { "gte": "now-1h"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
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
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
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
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
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
      ],
      "must_not": [
        {"match": {"src_ip": "10.0.2.5"}}
      ]
    }
  }
}

ddosDataQuery = {
  "query": {
    "bool": {
      "must": [
        {"match": {"type": "Ddospot"}},
        {"range": {"@timestamp": {"gte": "now-10m"}}}
      ],
      "must_not": [
        {"match": {"src_ip": "10.0.2.5"}}
      ]
    }
  }
}

sentrypeerDataQuery = {
   "query": {
      "bool": {
        "must": [
          {"match": {"type": "Sentrypeer"}},
          {"range": {"@timestamp": { "gte": "now-10m"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
        ]
      }
   }
}

redisDataQuery = {
   "query": {
      "bool": {
        "must": [
          {"match": {"type": "Redishoneypot"}},
          {"range": {"@timestamp": { "gte": "now-1d"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
        ]
      }
   }
}

ipphoneyDataQuery = {
   "query": {
      "bool": {
        "must": [
          {"match": {"type": "Ipphoney"}},
          {"range": {"@timestamp": { "gte": "now-1d"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
        ]
      }
   }
}

honeytrapDataQuery = {
    "query": {
      "bool": {
        "must": [
          {"match": {"type": "Honeytrap"}},
          {"range": {"@timestamp": { "gte": "now-1h"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
        ]
      }
   }
}

heraldingDataQuery = {
    "query": {
      "bool": {
        "must": [
          {"match": {"type": "Heralding"}},
          {"range": {"@timestamp": { "gte": "now-1h"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
        ]
      }
   }
}

fattDataQuery = {
    "query": {
      "bool": {
        "must": [
          {"match": {"type": "Fatt"}},
          {"range": {"@timestamp": { "gte": "now-10m"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
        ]
      }
   }
}

elasticPotDataQuery = {
    "query": {
      "bool": {
        "must": [
          {"match": {"type": "ElasticPot"}},
          {"range": {"@timestamp": { "gte": "now-1h"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
        ]
      }
   }
}

dicompotDataQuery = {
    "query": {
      "bool": {
        "must": [
          {"match": {"type": "Dicompot"}},
          {"range": {"@timestamp": { "gte": "now-1h"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
        ]
      }
   }
}

ciscoasaDataQuery = {
    "query": {
      "bool": {
        "must": [
          {"match": {"type": "Ciscoasa"}},
          {"range": {"@timestamp": { "gte": "now-1h"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
        ]
      }
   }
}

adbhoneyDataQuery = {
    "query": {
      "bool": {
        "must": [
          {"match": {"type": "Adbhoney"}},
	  {"exists": {"field": "src_ip"}},
          {"range": {"@timestamp": { "gte": "now-1h"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
        ]
      }
   }
}

citrixDataQuery = {
    "query": {
      "bool": {
        "must": [
          {"match": {"type": "CitrixHoneyPot"}},
          {"range": {"@timestamp": { "gte": "now-1h"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
        ]
      }
   }
}

dionaeaDataQuery = {
    "query": {
      "bool": {
        "must": [
          {"match": {"type": "Dionaea"}},
          {"range": {"@timestamp": { "gte": "now-1h"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
        ]
      }
   }
}

conpotDataQuery = {
    "query": {
      "bool": {
        "must": [
          {"match": {"type": "Conpot"}},
          {"range": {"@timestamp": { "gte": "now-1h"}}}
        ],
        "must_not": [
          {"match": {"src_ip": "10.0.2.5"}}
        ]
      }
   }
}

# Functions to store fetched data
def getMailoneyData(hitsArray):
	headers = ["IP","Data"]
	data = []
	for hit in hitsArray:
		if ip_address(hit["_source"]["src_ip"]).is_global:
			dataObj = [hit["_source"]["src_ip"],hit["_source"]["data"]]
			data.append(dataObj)
	writeToFile(data, headers, "MailoneyData.csv")
	return addToElastic(getHitCount(hitsArray), "Mailoney")

def getCowrieData(hitsArray):
	headers = ["IP","Reputation","Username","Password","Message","CowrieEventId"]
	data = []
	for hit in hitsArray:
		if ip_address(hit["_source"]["src_ip"]).is_global:
			dataObj = [hit["_source"]["src_ip"],hit["_source"]["ip_rep"],hit["_source"]["username"],hit["_source"]["password"],hit["_source"]["message"],hit["_source"]["eventid"]]
			data.append(dataObj)
	writeToFile(data, headers, "CowrieData.csv")
	return addToElastic(getHitCount(hitsArray), "Cowrie")

def getSuricataData(hitsArray):
	return addToElastic(getHitCount(hitsArray), "Suricata")

def getDdosData(hitsArray):
	return addToElastic(getHitCount(hitsArray), "Ddospot")

def getSentrypeerData(hitsArray):
	return addToElastic(getHitCount(hitsArray), "Sentrypeer")

def getTannerData(hitsArray):
        return addToElastic(getHitCount(hitsArray), "Tanner")

def getRedisData(hitsArray):
        return addToElastic(getHitCount(hitsArray), "Redishoneypot")

def getIpphoneyData(hitsArray):
        return addToElastic(getHitCount(hitsArray), "Ipphoney")

def getHoneytrapData(hitsArray):
        return addToElastic(getHitCount(hitsArray), "Honeytrap")

def getHeraldingData(hitsArray):
        return addToElastic(getHitCount(hitsArray), "Heralding")

def getFattData(hitsArray):
        return addToElastic(getHitCount(hitsArray), "Fatt")

def getElasticPotData(hitsArray):
        return addToElastic(getHitCount(hitsArray), "ElasticPot")

def getDicompotData(hitsArray):
        return addToElastic(getHitCount(hitsArray), "Dicompot")

def getCiscoasaData(hitsArray):
        return addToElastic(getHitCount(hitsArray), "Ciscoasa")

def getAdbhoneyData(hitsArray):
        return addToElastic(getHitCount(hitsArray), "Adbhoney")

def getCitrixData(hitsArray):
	return addToElastic(getHitCount(hitsArray), "CitrixHoneyPot")

def getDionaeaData(hitsArray):
        return addToElastic(getHitCount(hitsArray), "Dionaea")

def getConpotData(hitsArray):
        return addToElastic(getHitCount(hitsArray), "Conpot")

def execute():
	deleted = deleteFromElastic()
	honeyPots = [
	        {'function': getTannerData, 'query': tannerDataQuery},
        	{'function': getMailoneyData, 'query': mailoneyDataQuery},
	        {'function': getCowrieData, 'query': cowrieDataQuery},
		{'function': getSuricataData, 'query': suricataDataQuery},
		{'function': getSentrypeerData, 'query': sentrypeerDataQuery},
		{'function': getRedisData, 'query': redisDataQuery},
		{'function': getIpphoneyData, 'query': ipphoneyDataQuery},
		{'function': getHoneytrapData, 'query': honeytrapDataQuery},
		{'function': getHeraldingData, 'query': heraldingDataQuery},
		{'function': getDdosData, 'query': ddosDataQuery},
		{'function': getFattData, 'query': fattDataQuery},
		{'function': getElasticPotData, 'query': elasticPotDataQuery},
		{'function': getDicompotData, 'query': dicompotDataQuery},
		{'function': getCiscoasaData, 'query': ciscoasaDataQuery},
		{'function': getAdbhoneyData, 'query': adbhoneyDataQuery},
		{'function': getCitrixData, 'query': citrixDataQuery},
		{'function': getDionaeaData, 'query': dionaeaDataQuery},
		{'function': getConpotData, 'query': conpotDataQuery}
        ]
	headers = {
		'Content-Type': 'application/json',
	}
	url = "http://localhost:64298/*/_search?size=10000&pretty=true"
	created = 0
	updated = 0
	failed = 0
	for pot in honeyPots:
		hits = requests.post(url, json=pot['query'], headers=headers).json()['hits']['hits']
		pCreated, pUpdated, pFailed = pot['function'](hits)
		created+=pCreated
		updated+=pUpdated
		failed+=pFailed

	print("\n[+] *********************************************")
	print("[+] " + str(created) + " new IPs Added.")
	print("[+] " + str(updated) + " IPs Updated.")
	print("[+] " + str(deleted) + " IPs Deleted.")
	print("[+] " + str(failed) + " Failed.")
	print("[+] *********************************************\n")

execute()
