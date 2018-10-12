# jiraextractor
Jiraextractor is a simple python script to download all the info about the issues and their changelogs in csv format. 

## Installation

First make sure all the libraries are installed. The Jira REST API and Pandas are required.

   `pip install jira pandas`
   
The JIRA Python API library eases the use of the JIRA REST API from Python and it has been used in production for years. See the documentation for full details. http://jira.readthedocs.io/en/latest/

## Usage

`jiraextractor -s JIRA_URL --project PROJECT_NAME [-u,--username] [-p, --password] [--issuefile] [--changelogfile] [--startdate] [--enddate]`

This example extracts all the issues and the changelog of the Spring project XD from 01-Jan-2016 to 01-Feb-2016

`python jiraextractor.py -s https://jira.atlassian.com --project JRA --startdate 2016-01-01 --enddate 2016-02-01`
