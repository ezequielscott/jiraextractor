# jiraextractor
Jiraextractor is a simple python script that connects with a JIRA server instance and download all the issues and their changelogs in csv format. 

## Installation

This script works with Python 3.X.

1. create a virtual environment (https://docs.python.org/3/library/venv.html)
   * `$ python -m venv env`
2. activate the virtual environment
   * `$ .\env\Scripts\activate.bat` (Win)
   * `$ source env/bin/activate` (Linux, MacOS) 
3. install all the dependencies 
   * `$ pip install -r requirements.txt`
   
The JIRA Python API library eases the use of the JIRA REST API from Python and it has been used in production for years. See the documentation for full details. http://jira.readthedocs.io/en/latest/

## Script usage

`jiraextractor -s JIRA_URL --project PROJECT_KEY [-u, --username] [-p, --password] [--issuefile] [--changelogfile] [--startdate] [--enddate] [--anonymize=False] [--parsefile] [-b, --blocksize]`

## Example:

4. extract the data. This example extracts all the issues and the changelog of the Spring project XD from 18-Feb-2014 to 20-Feb-2014 
   * `$ python jiraextractor.py -s https://jira.spring.io/ --project XD --startdate "2014-02-18" --enddate "2014-02-20"`
5. As a result, three files are created:
   * jira.spring.io-XD-changelog.csv : each row represents a change made on a issue report
   * jira.spring.io-XD-issues.csv : each row represents an issue report
   * XD-raw : contains issue report data without any pre-processing step (for example, the changelog is embedded in a field using json)

## Utils

If something goes wrong, it is possible to parse the temporal file *-raw.csv with the script `parse-raw-file.csv`
