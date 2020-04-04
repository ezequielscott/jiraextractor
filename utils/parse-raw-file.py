#!/usr/bin/env python
"""
SYNOPSIS

    parse-raw-file FILENAME [SPLIT]

DESCRIPTION

    This script extracts the issues and the changelog from a file *-raw.csv that has been extracted using the jiraextractor

EXAMPLES

    parse-raw-file.py -s MDL-raw.csv

AUTHOR

    Ezequiel Scott <ezequielscott@gmail.com>

VERSION

    $1.0$
"""

import sys, os, traceback, argparse
import logging, time
import pandas as pd
import ast
import numpy as np

def init_logger():
    global logger

    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)


def parse_raw(df):
    df['ch'] = df['changelog'].apply(lambda x : ast.literal_eval(x)['histories'])
    df['ch0'] = df['ch'].apply( lambda x : [ pd.io.json.json_normalize(e) for e in x ])

    # attrs is dictionary
    def concat_attrs(lst, attrs):
        if len(lst) != 0:
            if isinstance(lst, dict):
                pdf = pd.concat(lst, sort=False)
            else:  #probably a list of dfs
                pdf = pd.concat([x for x in lst])
                
            for k in attrs:
                pdf[k] = attrs[k]
        else:
            pdf = pd.DataFrame()
        return pdf

    df['ch1'] = df.apply(lambda x: concat_attrs(x['ch0'], {'key' : x['key']}), axis=1)

    # first unwrap
    df2 = pd.concat([pd.DataFrame(df['ch1'][i]) for i in df.index], ignore_index=True, sort=False)

    # now do the same with the histories
    df2['items_h'] = df2.loc[:, 'items'].apply( lambda x : [ pd.io.json.json_normalize(e) for e in x ])
    
    df2['items_h2'] = df2.apply(lambda x: concat_attrs(x['items_h'], {'key' : x['key'], 'created' : x['created'], 'author' : x['author.key']}), axis=1)

    # second unwrap (it contains all the changelog)
    changelog = pd.concat([df2['items_h2'][i] for i in df2.index], ignore_index=True, sort=False)

    # add the field project
    changelog['project'] = changelog['key'].apply(lambda x : x.split('-')[0])

    # get the issues
    df4 = df['fields'].apply(lambda x : pd.io.json.json_normalize(ast.literal_eval(x)))

    issues = pd.concat([df4[i] for i in df4.index], ignore_index=True, sort=False)
    issues['key'] = df['key']

    return issues, changelog


def process_file(FILENAME, SPLIT):
    SPLIT = int(SPLIT)
    df = pd.read_csv(FILENAME)

    #df.dropna(axis=1, how='all', inplace=True)

    # remove bad entries
    df = df[df['changelog']!='changelog']
    chunks = np.array_split(df, SPLIT)
    for i, dfc in enumerate(chunks):
        logger.info("Processing file with shape {:} at chunk {:}".format(dfc.shape, i))
        issues, changelog = parse_raw(dfc)
        logger.info("Saving chunks to file...")
        issues.to_csv(FILENAME + 'issues' + str(i) + '.csv', encoding='utf-8', header=True, index=False, line_terminator="\n")
        changelog.to_csv(FILENAME + 'changelog' + str(i) + '.csv', encoding='utf-8', header=True, index=False, line_terminator="\n")

    ###############################
    # Join the files

    l = []
    for i in range(SPLIT):
        if i == 0: 
            df = pd.read_csv(FILENAME + 'issues' + str(i) + '.csv')
        else:
            df = pd.read_csv(FILENAME + 'issues' + str(i) + '.csv', skiprows=0)

        l.append(df)

    fulldf = pd.concat(l, axis=0)
    fulldf.to_csv(FILENAME + "-issues.csv", encoding='utf-8', header=True, index=False, line_terminator="\n")

    ### I have to do it twice (batch) because of memory issues
    l = []
    for i in range(SPLIT):
        if i == 0: 
            df = pd.read_csv(FILENAME + 'changelog' + str(i) + '.csv')
        else:
            df = pd.read_csv(FILENAME + 'changelog' + str(i) + '.csv', skiprows=0)

        l.append(df)

    fulldf = pd.concat(l, axis=0)
    fulldf.to_csv(FILENAME + "-changelog.csv", encoding='utf-8', header=True, index=False, line_terminator="\n")


if __name__ == '__main__':
    try:

        parser = argparse.ArgumentParser(usage=globals()['__doc__'])

        parser.add_argument("-f", "--filename", dest="FILENAME", required=True, help="Filename of the file to parse (ending with *-raw.csv", default='')
        parser.add_argument("-s", "--split", dest="SPLIT", required=False, help="Number of volumes to split during the processing. Recommended if the file is too large.", default='1')
        
        args = parser.parse_args()

        start_time = time.time()
        init_logger()

        process_file(args.FILENAME, args.SPLIT)

        logger.info('Total elapsed time: {:.2f}s'.format(time.time() - start_time))
        logger.info("Done.")

    except KeyboardInterrupt as e:  # Ctrl-C
        logging.warning('Interrupted by the user.')
        raise e
    except SystemExit as e:  # sys.exit()
        logging.warning('System exit.')
        raise e
    except Exception as e:
        logger.error("Something went wrong and I didn\'t think about it. Please report the bug https://github.com/ezequielscott/jiraextractor/issues.")
        logger.error(str(e))
        traceback.print_exc()
        os._exit(1)
