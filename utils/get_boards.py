import sys, os, traceback, argparse
from datetime import datetime
import time
import re
import ast

from jira import JIRA
import pandas as pd
import numpy as np
import logging
import json

# importing the requests library 
import requests 
from base64 import b64encode

### Parameters ###
api_login = ''
api_password = ''
base_url = "https://tracker.moodle.org"


def connect(url, username='', password=''):
    if username and password:
        jira = JIRA(server=url, basic_auth=(username, password))
    else:
        jira = JIRA(url)
    return jira

jira = connect(base_url, api_login, api_password)

boards = jira.boards() 
# get all the boards
boardsdf = pd.DataFrame([{"board.name": b.name, "board.id": b.id} for b in boards ])
boardsdf

all = []
# Get the sprints in each specific board
for i, b in boardsdf.iterrows():
    id = b["board.id"]

    # get issues from backlog
    # /rest/agile/1.0/board/{boardId}/backlog

    URL = base_url + '/rest/agile/1.0/board/' + str(id) + '/backlog'

    # get issues from board
    # GET /rest/agile/1.0/board/{boardId}/issue
    # for example https://tracker.moodle.org/rest/agile/1.0/board/{boardId}/issue

    URL = base_url + '/rest/agile/1.0/board/' + str(id) + '/issue'

    #auth
    token =  b64encode((api_login + ':' + api_password).encode('UTF-8')).decode('UTF-8')

    r = requests.get(URL, headers={'Authorization': 'Basic ' + token})

    # extracting data in json format 
    data = r.json() 

    datadf = pd.DataFrame(data)
    if datadf.shape[0] > 0:
        issues = datadf['issues'].apply(pd.Series)[['key', 'fields']]
        issues = pd.concat([issues['key'], issues['fields'].apply(pd.Series)], axis=1)
        issues['board.name'] = b["board.name"]
        issues['board.id'] = b['board.id']

        all.append(issues)

allissues = pd.concat(all, axis=0)
allissues.to_csv('MDL-issues-agileinfo.csv')
