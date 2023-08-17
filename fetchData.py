#!/usr/bin/python3
import requests
import json
import uuid
import csv
from datetime import datetime
from ipaddress import ip_address

# Index creation
#curl -XPUT "http://localhost:64298/ipfeed?pretty"
#-d '{"settings": {"number_of_shards": 1}},{"mappings": {"_default": {"_timestamp": {"enabled": true, "store": true, "format": "basic_date_time"}}}}'
#-H 'Content-Type: application/json'

# Write data into CSV
#urlBase = https://
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
                try:
                        IP = obj["_source"]["src_ip"]
                        if ip_address(IP).is_global:
                                ipList.append(IP)
                except:
                        print("[+] Parse failed")
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
        searchUrl = "http://localhost:64298/ipfeed/_search?size=10000&pretty=true"
        headers = {'Content-Type': 'application/json'}
        searchQuery = {
                "query":
                        {"bool":
                                {"must":
                                        [
                                                {"range":
                                                        {"LastDate": {"lt": "now-1d"}}
                                                }
                                        ]
                                }
                        }
                }
        try:
                hits = requests.post(searchUrl, json=searchQuery, headers=headers).json()['hits']['hits']
                if len(hits) > 0:
                        print("[+] Deleting " + str(len(hits)) + " documents...")
                        for hit in hits:
                                deleteUrl = 'http://localhost:64298/ipfeed/_doc/' + hit["_id"] + '?pretty'
                                response = requests.delete(deleteUrl, headers=headers).json()
                                print("[+] indexID: " + hit["_id"] + " result: " + response["result"])
                else:
                        print("[+] No old IPs")
                return len(hits)
        except:
                print("[+] IP Feed Empty")
                return 0

# Add Hits Data to Elastic
def addToElastic(data, honeyPot):
        now = datetime.now()
        date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        searchUrl = "http://localhost:64298/ipfeed/_search?size=10000&pretty=true"
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
                uuid1 = uuid.uuid4()
                insertQuery = {
                        "UUID": str(uuid1),
                        "IP": obj[0],
                        "Count": obj[1],
                        "Sources": honeyPot,
                        "FirstDate": date,
                        "LastDate": date,
                }
                try:
                        response = requests.post(searchUrl, json=searchQuery, headers=headers).json()['hits']['hits']

                        if response != []:
                                id = response[0]['_id']
                                uuid2 = response[0]['_source']['UUID']
                                firstDate = response[0]['_source']['FirstDate']
                                sources = response[0]['_source']['Sources']
                                count = response[0]['_source']['Count']
                                updateUrl = "http://localhost:64298/ipfeed/_update/" + id
                                if sources.find(honeyPot) == -1:
                                        updateQuery = {
                                                "doc": {
                                                        "UUID": uuid2,
                                                        "IP": obj[0],
                                                        "Count": int(obj[1])+int(count),
                                                        "Sources": sources + ", " + honeyPot,
                                                        "FirstDate": firstDate,
                                                        "LastDate": date
                                                }
                                        }
                                        response = requests.post(updateUrl, json=updateQuery, headers=headers).json()
                                        if response['result'] != 'updated':
                                                failed+=1
                                        else:
                                                updated+=1
                                        #print("[+] indexID: " + response['_id'] + " result: " + response['result'])
                                else:
                                        updateQuery = {
                                                "doc": {
                                                        "UUID": uuid2,
                                                        "IP": obj[0],
                                                        "Count": int(obj[1])+int(count),
                                                        "Sources": sources,
                                                        "FirstDate": firstDate,
                                                        "LastDate": date
                                                }
                                        }
                                        response = requests.post(updateUrl, json=updateQuery, headers=headers).json()
                                        if response['result'] != 'updated':
                                                failed+=1
                                        else:
                                                updated+=1
                                        #print("[+] indexID: " + response['_id'] + " result: " + response['result'])
                        else:
                                response = requests.post(insertUrl, json=insertQuery, headers=headers).json()
                                if response['result'] != 'created':
                                        failed+=1
                                else:
                                        created+=1
                                #print("[+] indexID: " + response['_id'] + " result: " + response['result'])
                except:
                        print("[+] IP Feed Empty")
                        response = requests.post(insertUrl, json=insertQuery, headers=headers).json()
                        if response['result'] != 'created':
                                failed+=1
                        else:
                                created+=1
                        #print("[+] indexID: " + response['_id'] + " result: " + response['result'])
        return created, updated, failed

# Function to return custmized search query
def customSearchQuery(honeyPot, time, customMatchFields, customNonMatchFields):
        if len(customMatchFields) > 0 or len(customNonMatchFields) > 0:
                musts = [{"match": {"type": honeyPot}}, {"range": {"@timestamp": { "gte": time}}}]
                mustNots = [{"match": {"src_ip": "10.0.2.5"}}]
                if len(customMatchFields) > 0:
                        for field in customMatchFields:
                                musts.append(field)

                if len(customNonMatchFields) > 0:
                        for field in customNonMatchFields:
                                musts.append(field)
                searchQuery = {
                        "query": {
                                "bool": {
                                        "must": musts,
                                        "must_not": mustNots
                                }
                        }
                }
        else:
                searchQuery = {
                        "query": {
                                "bool": {
                                        "must": [
                                                {"match": {"type": honeyPot}},
                                                {"range": {"@timestamp": { "gte": time}}}
                                        ],
                                        "must_not": [
                                                {"match": {"src_ip": "10.0.2.5"}}
                                        ]
                                }
                        }
                }
        return searchQuery

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

def writeToJson_csv():
        searchUrl = "http://localhost:64298/ipfeed/_search?size=10000&pretty=true"
        headers = {
            'Content-Type': 'application/json',
        }
        query = {
            "query":
                {"bool":
                    {"must":[
                        {"range":{"LastDate": {"gte": "now-1h"}}}
                    ]
                }
            }
        }

        hits = requests.post(searchUrl, json=query, headers=headers).json()['hits']['hits']
        outFile = open('ipfeed.json', 'w')
        for hit in hits:
            json.dump(hit['_source'], outFile)
            outFile.write(",\n")
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


def execute():
        deleted = deleteFromElastic()
        honeyPots = [
                {'function': getTannerData, 'query': customSearchQuery("Tanner", "now-1h", [], [])},
                {'function': getMailoneyData, 'query': customSearchQuery("Mailoney", "now-1h", [], [])},
                {'function': getCowrieData, 'query': customSearchQuery("Cowrie", "now-1h", [{'exists': {'field': 'username'}}, {'exists': {'field': 'ip_rep'}}], [])},
                {'function': getSuricataData, 'query': customSearchQuery("Suricata", "now-10m", [{"match": {"event_type": "alert"}}], [])},
                {'function': getSentrypeerData, 'query': customSearchQuery("Sentrypeer", "now-1h", [], [])},
                {'function': getRedisData, 'query': customSearchQuery("Redishoneypot", "now-1h", [], [])},
                {'function': getIpphoneyData, 'query': customSearchQuery("Ipphoney", "now-1h", [], [])},
                {'function': getHoneytrapData, 'query': customSearchQuery("Honeytrap", "now-1h", [], [])},
                {'function': getHeraldingData, 'query': customSearchQuery("Heralding", "now-1h", [], [])},
                {'function': getDdosData, 'query': customSearchQuery("Ddospot", "now-1h", [], [])},
                {'function': getFattData, 'query': customSearchQuery("Fatt", "now-1h", [], [])},
                {'function': getElasticPotData, 'query': customSearchQuery("ElasticPot", "now-1h", [], [])},
                {'function': getDicompotData, 'query': customSearchQuery("Dicompot", "now-1h", [], [])},
                {'function': getCiscoasaData, 'query': customSearchQuery("Ciscoasa", "now-1h", [], [])},
                {'function': getAdbhoneyData, 'query':  customSearchQuery("Adbhoney", "now-1h", [{"exists": {"field": "src_ip"}}], [])},
                {'function': getCitrixData, 'query':  customSearchQuery("CitrixHoneyPot", "now-1h", [], [])},
                {'function': getDionaeaData, 'query': customSearchQuery("Dionaea", "now-1h", [], [])},
                {'function': getConpotData, 'query': customSearchQuery("Conpot", "now-1h", [], [])}
        ]
        headers = {
                'Content-Type': 'application/json',
        }
        url = "http://localhost:64298/logstash-20*/_search?size=10000&pretty=true"
        created = 0
        updated = 0
        failed = 0
        for pot in honeyPots:
                hits = requests.post(url, json=pot['query'], headers=headers).json()['hits']['hits']
                pCreated, pUpdated, pFailed = pot['function'](hits)
                created+=pCreated
                updated+=pUpdated
                failed+=pFailed

        now = datetime.now()
        date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        print("\n[+] *********************************************")
        print("[+] Date " + str(date))
        print("[+] " + str(created) + " new IPs Added.")
        print("[+] " + str(updated) + " IPs Updated.")
        print("[+] " + str(deleted) + " IPs Deleted.")
        print("[+] " + str(failed) + " Failed.")
        print("[+] *********************************************\n")
        summaryFile = open("fetchSummary.txt", "w")
        summaryFile.write("[+] *********************************************\n")
        summaryFile.write("[+] Date " + str(date) + "\n")
        summaryFile.write("[+] " + str(created) + " new IPs Added.\n")
        summaryFile.write("[+] " + str(updated) + " IPs Updated.\n")
        summaryFile.write("[+] " + str(deleted) + " IPs Deleted.\n")
        summaryFile.write("[+] " + str(failed) + " Failed.\n")
        summaryFile.write("[+] *********************************************\n")
        summaryFile.close()
        writeToJson_csv()

execute()