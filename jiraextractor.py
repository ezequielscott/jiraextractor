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
import ast

from jira import JIRA
import pandas as pd
import numpy as np
import logging


# from pexpect import run, spawn

def init_logger():
    global logger

    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler("{0}/{1}.log".format('.', 'lhv'))
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
    """
    This function parses a list of issues (JIRA API objects) into a pandas dataframe
    :param issues: a list of issues objects
    :return: two panda dataframes containing the issues and the changelog
    """

    logger.info('Parsing issues ...')

    df = pd.DataFrame()
    changelog = pd.DataFrame()

    for issue in issues:
        # get all the issue fields
        d = issue.raw['fields']
        d['key'] = issue.key
        df = df.append(d, ignore_index=True)

        # get all the entries in the changelog
        ch = issue.changelog

        for history in ch.histories:
            for item in history.items:
                d = {
                    'key': issue.key,
                    # author is not always present
                    'author': history.author.key if 'author' in dir(history) else np.nan,
                    'date': history.created,
                    'field': item.field,
                    'fieldtype': item.fieldtype,
                    'from': getattr(item, 'from'),
                    # getattr() must be used since 'from' is a special word in python and it makes item.from don't work 
                    'fromString': item.fromString,
                    'to': item.to,
                    'toString': item.toString
                }

                changelog = changelog.append(d, ignore_index=True)

    return df, changelog


def get_issues(jira, project, startdate='', enddate=''):
    """
    Get the issues from JIRA
    :param jira: connection object for the JIRA instance
    :param project: name of the project
    :param startdate: start date of the period we want to extract
    :param enddate: date date of the period we want to extract
    :return: a list of issue objects (JIRA API)
    """
    block_size = 1000
    block_num = 0
    all_issues = []

    jql = 'project={0}'.format(project)
    if startdate and enddate:
        jql = 'project={0} and created >= {1} and created <= {2}'.format(project, startdate, enddate)

    while True:
        start_idx = block_num * block_size
        logger.info('Searching for issues from %d to %d ...' % (start_idx + 1, start_idx + block_size))

        issues = jira.search_issues(jql, start_idx, block_size, expand='changelog')
        if len(issues) == 0:
            # Retrieve issues until there are no more to come
            logger.info('... no issues found')
            break
        block_num += 1
        logger.info('... %d issues retrieved' % len(issues))
        for issue in issues:
            # logger.info('%s: %s' % (issue.key, issue.fields.summary))
            all_issues.append(issue)
    logger.info('%d issues retrieved in total.' % len(all_issues))
    return all_issues

def get_changelog(issues):
    """
    Get the changelog of a collection of issues from JIRA
    :param issues: a dataframe containing JIRA issues as result of parse_issues function
    :return: a pandas dataframe with the changelog of all the issues passed as parameter
    """
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


def anonymize(df, changelog, fields_to_anonymize=["reporter", "creator", "assignee"]):
    """
    Process the dataframes with issues and changelog and make a given list of fields anonymous.
    :param df: a dataframe containing JIRA issues
    :param ch: a dataframe containing the changelog
    :param fields_to_anonymize: a list of strings indicating the fields that must be anonymized
    :return: two dataframes (issues, changelog) annonymized
    """
    df['creator'] = df['creator'].astype(str)
    df['assignee'] = df['assignee'].astype(str)
    df['reporter'] = df['reporter'].astype(str)

    df['creator'] = df['creator'].apply(lambda x : np.nan if x is None else ast.literal_eval(x))
    df['assignee'] = df['assignee'].apply(lambda x : np.nan if x is None else ast.literal_eval(x))
    df['reporter'] = df['reporter'].apply(lambda x : np.nan if x is None else ast.literal_eval(x))

    df['creator'] =  df['creator'].apply(lambda x: np.nan if x is None else x['key'])
    df['assignee'] = df['assignee'].apply(lambda x: np.nan if x is None else x['key'])
    df['reporter'] = df['reporter'].apply(lambda x: np.nan if x is None else x['key'])

    jirausers = []
    for field in fields_to_anonymize:
        if field in df.columns:
            jirausers = jirausers + df[field].values.tolist()

    jirausers = pd.unique(jirausers)

    to_replace = [ 'U' + str(i+1) for i in range(len(jirausers)) ]

    jirauserkeys = dict(zip(jirausers, to_replace))

    for field in fields_to_anonymize:
        if field in df.columns:
            df[field] = df[field].map(jirauserkeys)
    
    changelog['author'] = changelog['author'].map(jirauserkeys)

    return df, changelog


if __name__ == '__main__':
    try:
        init_logger()

        parser = argparse.ArgumentParser(usage=globals()['__doc__'])

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

        parser.add_argument("--anonymize", 
                            dest="ANON", 
                            required=False,
                            default='False', 
                            help="This flag (True or False) determines if the files should be anonymized or not. A list of stardard fields are considered for anonymization.")

        args = parser.parse_args()

        # if len(args) < 1:
        #    parser.error('missing argument')

        jira = connect(args.SERVER, args.USERNAME, args.PASSWORD)

        issues = get_issues(jira, args.PROJECT, args.STARTDATE, args.ENDDATE)
        df, changelog = parse_issues(issues)
        
        # anonymize
        if args.ANON != 'False':
            logger.info("Anonymizing...")
            df, changelog = anonymize(df, changelog)

        logger.info("Saving issues to file.")
        df.to_csv(args.FILENAME_ISSUES, encoding='utf-8', header=True, index=False, line_terminator="\n")

        logger.info("Saving changelog to file.")
        changelog.to_csv(args.FILENAME_CHANGELOG, encoding='utf-8', header=True, index=False, line_terminator="\n")

        logger.info("Done.")

        sys.exit(0)
    except KeyboardInterrupt as e:  # Ctrl-C
        raise e
    except SystemExit as e:  # sys.exit()
        raise e
    except Exception as e:
        print ('ERROR, UNEXPECTED EXCEPTION')
        print (str(e))
        traceback.print_exc()
        os._exit(1)
