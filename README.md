# jiraextractor
Jiraextractor is a simple python script to download all the issues and their changelogs in csv format. 

## Installation

This script works with Python 3.X.

First, make sure all the dependencies are installed. The Jira REST API and Pandas are required.

   `pip install -r requirements.txt`
   
The JIRA Python API library eases the use of the JIRA REST API from Python and it has been used in production for years. See the documentation for full details. http://jira.readthedocs.io/en/latest/

## Usage

`jiraextractor -s JIRA_URL --project PROJECT_NAME [-u,--username] [-p, --password] [--issuefile] [--changelogfile] [--startdate] [--enddate] [--anonymize=False]`

This example extracts all the issues and the changelog of the Spring project XD from 01-Jan-2016 to 01-Feb-2016

`python jiraextractor.py -s https://jira.spring.io --project XD --startdate 2013-02-18 --enddate 2013-02-20`
