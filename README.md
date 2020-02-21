# jiraextractor
Jiraextractor is a simple python script that connects with a JIRA server instance and download all the issues and their changelogs in csv format. 

## Installation

This script works with Python 3.X.

First, it is a good idea to create a virtual environment for the dependencies. https://docs.python.org/3/library/venv.html

Then, install all the dependencies.

   `pip install -r requirements.txt`
   
The JIRA Python API library eases the use of the JIRA REST API from Python and it has been used in production for years. See the documentation for full details. http://jira.readthedocs.io/en/latest/

## Usage

`jiraextractor -s JIRA_URL --project PROJECT_NAME [-u,--username] [-p, --password] [--issuefile] [--changelogfile] [--startdate] [--enddate] [--anonymize=False]`

This example extracts all the issues and the changelog of the Spring project XD from 18-Feb-2014 to 20-Feb-2014

`python jiraextractor.py -s https://jira.spring.io --project XD --startdate 2014-02-18 --enddate 2014-02-20`
