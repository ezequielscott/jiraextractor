#!/usr/bin/env python
"""
SYNOPSIS

    jiraextractor -s JIRA_URL --project PROJECT_NAME [-u, --username] [-p, --password] [--issuefile] [--changelogfile] [--startdate] [--enddate] [--anonymize=False] [--parsefile] [-b, --blocksize]

DESCRIPTION

    This script will extract data from a jira server instance. The data to extract is related to issues, and the changelog.

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
import json

# from pexpect import run, spawn

def init_logger():
    global logger

    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler("{0}/{1}.log".format('.', 'jiraextractor'))
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


def parse_issues2(df):
    start_time = time.time()

    logger.info('Parsing changelog...')

    df = pd.DataFrame(df)

    # remove wrong lines
    df = df[df['changelog']!='changelog']

    df['ch'] = df['changelog'].apply(lambda x : x['histories'])

    df['ch0'] = df['ch'].apply( lambda x : [ pd.io.json.json_normalize(e) for e in x ])

    # concat attrs stored in a dictionary
    def concat_attrs(lst, attrs):
        if len(lst) != 0:
            pdf = pd.concat(lst, sort=False)
            for k in attrs:
                pdf[k] = attrs[k]
        else:
            pdf = None
        return pdf

    df['ch1'] = df.apply(lambda x: concat_attrs(x['ch0'], {'key' : x['key']}), axis=1)

    # first unwrap
    df2 = pd.concat([df['ch1'][i] for i in df.index], ignore_index=True, sort=False)
        
    # now do the same with the histories
    df2['items_h'] = df2['items'].apply( lambda x : [ pd.io.json.json_normalize(e) for e in x ])

    df2['items_h2'] = df2.apply(lambda x: concat_attrs(x['items_h'], {'key' : x['key'], 'created' : x['created'], 'author' : x[get_author_key2(x)]}), axis=1)

    # second unwrap (it contains all the changelog)
    changelog = pd.concat([df2['items_h2'][i] for i in df2.index], ignore_index=True, sort=False)

    # add the field project
    changelog['project'] = changelog['key'].apply(lambda x : x.split('-')[0])

    logger.info('Parsing issue list...')

    df['fields2'] = df['fields'].apply( lambda e : pd.io.json.json_normalize(e))
    issues = pd.concat([df['fields2'][i] for i in df.index], ignore_index=True, sort=False)
    issues['key'] = df['key']

    # add the field project
    issues['project'] = issues['key'].apply(lambda x : x.split('-')[0])

    logger.info('Elapsed parsing time: {:.2f}s'.format(time.time() - start_time))

    return issues, changelog


def parse_issues(issues):
    """
    This function parses a list of issues (JIRA API objects) into a pandas dataframe
    :param issues: a list of issues objects
    :return: two panda dataframes containing the issues and the changelog
    """

    start_time = time.time()
    logger.info('Parsing %d issues ... ' % len(issues))
    issues_len = len(issues)
    print_progress_bar(0, issues_len, 'Progress:', 'Complete', 2, 50)

    df = pd.DataFrame()
    changelog = pd.DataFrame()

    for i, issue in enumerate(issues):
        # get all the issue fields
        d = issue['fields']
        d['key'] = issue['key']
        df = df.append(d, ignore_index=True)

        # get all the entries in the changelog
        ch = issue['changelog']

        for history in ch['histories']:
            for item in history['items']:

                d = {
                    'key': issue['key'],
                    'author': get_author_string(history),
                    'date': history['created'],
                    'field': item['field'],
                    'fieldtype': item['fieldtype'],
                    'from': item['from'],
                    # getattr() must be used since 'from' is a special word in python and it makes item.from don't work
                    'fromString': item['fromString'],
                    'to': item['to'],
                    'toString': item['toString']
                }

                changelog = changelog.append(d, ignore_index=True)

        print_progress_bar(i + 1, issues_len, 'Progress:', 'Complete', 2, 50)

    logger.info('Elapsed parsing time: {:.2f}s'.format(time.time() - start_time))

    return df, changelog


def get_author_string(history):
    """
    Get author string for issue history record
    @params:
        history - Required : JIRA history record object
    """
    key = get_author_key(history)
    return np.nan if key is None else history['author'][key]


def get_author_key(history):
    """
    Get author string value key for issue history record
    @params:
        history - Required : JIRA history record object
    """
    keys = ['key', 'author.key', 'accountId', 'author.accountId', 'displayName', 'author.displayName']

    for k in keys:
        if k in history['author']:
            return k

    return None


def get_author_key2(history):
    """
    Get author string value key for issue history record (used in parse_issues2())
    @params:
        history - Required : history dataframe row
    """
    keys = ['author.key', 'author.accountId', 'author.displayName']

    for k in keys:
        if k in history:
            return k

    return np.nan


def print_progress_bar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', print_end = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        print_end   - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    if total < 1:
        return

    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = print_end)
    # Print New Line on Complete
    if iteration == total:
        print()


def get_issues(jira, project='', startdate='', enddate='', block_size=1000):
    """
    Get the issues from JIRA
    :param jira: connection object for the JIRA instance
    :param project: project key
    :param startdate: start date of the period we want to extract
    :param enddate: date date of the period we want to extract
    :return: a list of issue objects (JIRA API)
    """
    all_issues = []

    if project:
        return get_issues_for_project(jira, project, startdate, enddate, block_size)
    else:
        for p in jira.projects():
            try:
                all_issues.extend(get_issues_for_project(jira, p.key, startdate, enddate))
            except Exception as e:
                logger.error('Error getting project with key %s: %s' % (p, e))

    return all_issues

def get_issues_for_project (jira, project, startdate='', enddate='', block_size=1000):
    """
    Get the issues from JIRA for the specific project name
    :param jira: connection object for the JIRA instance
    :param project: project key
    :param startdate: start date of the period we want to extract
    :param enddate: date date of the period we want to extract
    :param block_size: size of a block (batch) of issues retrieved at once from JIRA
    :return: a list of issue objects (JIRA API)
    """
    block_num = 0
    all_issues = []

    logger.info('Project name: %s' % (project))

    jql = 'project={0}'.format(project)
    if startdate and enddate:
        jql = 'project=\'{0}\' and created >= {1} and created <= {2}'.format(project, startdate, enddate)

    while True:
        start_idx = block_num * block_size
        logger.info('Searching for issues from %d to %d ...' % (start_idx + 1, start_idx + block_size))

        query = jira.search_issues(jql, start_idx, block_size, expand='changelog', json_result=True)

        if len(query['issues']) == 0:
            # Retrieve issues until there are no more to come
            logger.info('... no issues found')
            break
        block_num += 1
        logger.info('... %d issues retrieved' % len(query['issues']))

        df = pd.DataFrame(query['issues'])
        if block_num == 1:
            # first block write the header
            df.to_csv(project+'-raw.csv', mode='a', encoding='utf-8', header=True, index=False, line_terminator="\n")
        else:
            df.to_csv(project+'-raw.csv', mode='a', encoding='utf-8', header=False, index=False, line_terminator="\n")

		# Appending to file
        #with open("tmp.json", 'a') as outfile:
        #    outfile.write(json.dumps(issues))
        #    outfile.write(",")
        #    outfile.close()

        #logger.info('Saved to tmp json file')

        #for issue in issues:
            # logger.info('%s: %s' % (issue.key, issue.fields.summary))
        all_issues.extend(query['issues'])

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


def anonymize(df, changelog, fields_to_anonymize=["reporter.key", "creator.key", "assignee.key"]):
    """
    Process the dataframes with issues and changelog and make a given list of fields anonymous.
    :param df: a dataframe containing JIRA issues
    :param ch: a dataframe containing the changelog
    :param fields_to_anonymize: a list of strings indicating the fields that must be anonymized
    :return: two dataframes (issues, changelog) annonymized
    """
    # df['creator'] = df['creator'].astype(str)
    # df['assignee'] = df['assignee'].astype(str)
    # df['reporter'] = df['reporter'].astype(str)

    # df['creator'] = df['creator'].apply(lambda x : np.nan if x is None else ast.literal_eval(x))
    # df['assignee'] = df['assignee'].apply(lambda x : np.nan if x is None else ast.literal_eval(x))
    # df['reporter'] = df['reporter'].apply(lambda x : np.nan if x is None else ast.literal_eval(x))

    # df['creator'] =  df['creator'].apply(lambda x: np.nan if x is None else x['key'])
    # df['assignee'] = df['assignee'].apply(lambda x: np.nan if x is None else x['key'])
    # df['reporter'] = df['reporter'].apply(lambda x: np.nan if x is None else x['key'])

    # The following code will anonymize the default user fields
    DEFAULT_USER_FIELDS = ["reporter.key", "creator.key", "assignee.key"]
    jirausers = []
    for field in DEFAULT_USER_FIELDS:
        if field in df.columns:
            jirausers = jirausers + df[field].dropna().values.tolist()

    jirausers = pd.unique(jirausers)

    to_replace = [ 'U' + str(i+1) for i in range(len(jirausers)) ]

    jirauserkeys = dict(zip(jirausers, to_replace))
 
    for field in DEFAULT_USER_FIELDS:
        if field in df.columns:
            df[field] = df[field].map(jirauserkeys, na_action='ignore')

    changelog['author'] = changelog['author'].map(jirauserkeys)

    return df, changelog


if __name__ == '__main__':
    try:
        init_logger()

        parser = argparse.ArgumentParser(usage=globals()['__doc__'])

        parser.add_argument("-u", "--username", dest="USERNAME", required=False, help="JIRA username", default='')
        parser.add_argument("-p", "--password", dest="PASSWORD", required=False, help="JIRA password", default='')
        parser.add_argument("-s", "--server", dest="SERVER", required=False, help="URL address to the server")
        parser.add_argument("--project", dest="PROJECT", required=False, help="JIRA project key", default='')

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

        parser.add_argument("--parsefile", dest="PARSEFILE", required=False, help="Parse a csv file with issues (file ending with -raw)")

        parser.add_argument("-b",
                            "--blocksize",
                            dest="BLOCK_SIZE",
                            help="The size of a block (batch) of issues retrieved at once from JIRA",
                            required=False,
                            default=1000)

        args = parser.parse_args()

        start_time = time.time()

        if (args.PARSEFILE):
            issues = pd.read_csv(args.PARSEFILE)
            df, changelog = parse_issues2(issues)    # or parse_issues()
        else:
            jira = connect(args.SERVER, args.USERNAME, args.PASSWORD)

            issues = get_issues(jira, args.PROJECT, args.STARTDATE, args.ENDDATE, int(args.BLOCK_SIZE))
            df, changelog = parse_issues2(issues)    # or parse_issues()

            # anonymize
            if (args.ANON != 'False'):
                logger.info("Anonymizing...")
                df, changelog = anonymize(df, changelog)

        logger.info('Total elapsed time: {:.2f}s'.format(time.time() - start_time))

        # parse the server url to get build the filename
        from urllib.parse import urlparse
        o = urlparse(args.SERVER)
        DOMAIN = o.netloc.split(':')[0]

        logger.info("Saving issues to file.")
        df.to_csv(DOMAIN + '-' + args.PROJECT + '-' + args.FILENAME_ISSUES, encoding='utf-8', header=True, index=False, line_terminator="\n")

        logger.info("Saving changelog to file.")
        changelog.to_csv(DOMAIN + '-' + args.PROJECT + '-' + args.FILENAME_CHANGELOG, encoding='utf-8', header=True, index=False, line_terminator="\n")

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
