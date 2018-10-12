#!/usr/bin/env python
"""
SYNOPSIS

    jiraextractor -s JIRA_URL --project PROJECT_NAME [-u,--username] [-p, --password] [--issuefile] [--changelogfile] [--startdate] [--enddate]

DESCRIPTION

    This script will extract data from a jira server instance. The data to extract is related to
    issues, and the changelog. The optional argument -t allows for extracting records from Tempo plugin.

EXAMPLES

    This example extracts all the issues and the changelog of the Spring project XD from Jan-2016 to Feb-2016

    jiraextractor.py -s https://jira.atlassian.com --project JRA --startdate 2016-01-01 --enddate 2016-02-01

AUTHOR

    Ezequiel Scott <ezequielscott@gmail.com>

VERSION

    $1.0$
"""

import sys, os, traceback, argparse
from datetime import datetime
import time
import re

from jira import JIRA
import pandas as pd
import logging


# from pexpect import run, spawn

def init_logger():
    global logger

    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler("{0}/{1}.log".format('.', 'lhv.log'))
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)


def connect(url, username='', password=''):
    logger.info('Connecting to %s ...' % url)

    if username and password:
        jira = JIRA(server=url, basic_auth=(username, password))
    else:
        jira = JIRA(url)

    return jira


def parse_issues(issues):
    # Parse all the issues into a dataframe

    logger.info('Parsing issues ...')

    df = pd.DataFrame()
    for issue in issues:
        df = df.append(issue.raw['fields'], ignore_index=True)

    return df


def get_issues(jira, project, startdate='', enddate=''):
    block_size = 1000
    block_num = 0
    all_issues = []
    while True:
        start_idx = block_num * block_size
        logger.info('Getting issues from %d to %d ...' % (start_idx + 1, start_idx + block_size))

        jql = 'project={0}'.format(project)
        if startdate and enddate:
            jql = 'project={0} and created >= {1} and created <= {2}'.format(project, startdate, enddate)

        issues = jira.search_issues(jql, start_idx, block_size)
        if len(issues) == 0:
            # Retrieve issues until there are no more to come
            break
        block_num += 1
        for issue in issues:
            # logger.info('%s: %s' % (issue.key, issue.fields.summary))
            all_issues.append(issue)
    logger.info('%d issues retrieved.' % len(all_issues))
    return all_issues

def get_changelog(issues):
    logger.info('Getting the changelog ...')

    changelog = pd.DataFrame()

    for issue in issues:
        issue = jira.issue(issue.key, expand='changelog')
        ch = issue.changelog

        for history in ch.histories:
            for item in history.items:
                d = {
                    'key': issue.key,
                    'author': history.author,
                    'date': history.created,
                    'field': item.field,
                    'fieldtype': item.fieldtype,
                    'from': getattr(item, 'from'),
                    # because using item.from doesn't work, 'from' is a special word in python
                    'fromString': item.fromString,
                    'to': item.to,
                    'toString': item.toString
                }

                changelog = changelog.append(d, ignore_index=True)
    return changelog


if __name__ == '__main__':
    try:
        init_logger()

        parser = argparse.ArgumentParser(usage=globals()['__doc__'], version='$Id$')

        parser.add_argument("-u", "--username", dest="USERNAME", help="JIRA username", default='')
        parser.add_argument("-p", "--password", dest="PASSWORD", help="JIRA password", default='')
        parser.add_argument("-s", "--server", dest="SERVER", required=True, help="URL address to the server")
        parser.add_argument("--project", dest="PROJECT", required=True, help="Name of the JIRA project")

        parser.add_argument("--issuefile", dest="FILENAME_ISSUES", required=False, default='issues.csv', help="Name of file where the issues will be stored. Default 'issues.csv'")
        parser.add_argument("--changelogfile", dest="FILENAME_CHANGELOG", required=False, default='changelog.csv', help="Name of file where the changelog will be stored. Default 'changelog.csv'")

        #parser.add_argument("-t", help="Use this option if you want to retrieve workloads from Tempo")

        parser.add_argument("--startdate",
                            help="The start date (creation date) - format YYYY-MM-DD",
                            required=False,
                            dest="STARTDATE")

        parser.add_argument("--enddate",
                            help="The end date (creation date) - format YYYY-MM-DD",
                            required=False,
                            dest="ENDDATE")

        args = parser.parse_args()

        # if len(args) < 1:
        #    parser.error('missing argument')

        jira = connect(args.SERVER, args.USERNAME, args.PASSWORD)
        issues = get_issues(jira, args.PROJECT, args.STARTDATE, args.ENDDATE)
        df = parse_issues(issues)

        logger.info("Saving issues to file.")
        df.to_csv(args.FILENAME_ISSUES, encoding='utf-8', header=True, index=False, line_terminator="\n")

        changelog = get_changelog(issues)

        logger.info("Saving changelog to file.")
        changelog.to_csv(args.FILENAME_CHANGELOG, encoding='utf-8', header=True, index=False, line_terminator="\n")

        logger.info("Done.")

        sys.exit(0)
    except KeyboardInterrupt, e:  # Ctrl-C
        raise e
    except SystemExit, e:  # sys.exit()
        raise e
    except Exception, e:
        print 'ERROR, UNEXPECTED EXCEPTION'
        print str(e)
        traceback.print_exc()
        os._exit(1)
