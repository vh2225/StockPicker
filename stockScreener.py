import argparse as ap
import datetime
import json
import os
import re

import stockUtils


def stockScreen():
    stockSet = stockUtils.getStockFromFinviz()
    return stockGetStats(stockSet)


def stockGetStats(stockSet):
    stockList = sorted(stockSet)
    scraped_data = []
    for ticker in stockList:
        print("Fetching data for %s" % (ticker))
        scraped_data.append(stockUtils.getStat(ticker))
    return stockList, scraped_data


def doDiff():
    regex = re.compile(r'\d+-\d+-\d+$')
    # get all dirs
    all_subdirs = sorted([d for d in os.listdir('.') if os.path.isdir(d) and regex.match(d)], reverse=True)
    last2Runs = [all_subdirs]
    # filter out the last 2
    for dir in all_subdirs:
        if len(last2Runs) == 2:
            break
        last2Runs.append(dir)
    if len(last2Runs) == 2:
        new = set((line.strip() for line in open(last2Runs[0] + '/stockList.json')))
        old = set((line.strip() for line in open(last2Runs[1] + '/stockList.json')))
        with open('diff.txt', 'w') as diff:
            for line in new:
                if line not in old:
                    diff.write('[-] {}\n'.format(line))

            for line in old:
                if line not in new:
                    diff.write('[+] {}\n'.format(line))


def writeStats(stockList, scraped_data, suffix=''):
    dateStamp = datetime.datetime.now().strftime("%Y-%m-%d")
    dirName = '{}{}'.format(dateStamp, suffix)
    os.makedirs(dirName, exist_ok=True)
    script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in
    # write companyList
    compList = "{}/stockList.json".format(dirName, suffix)
    abs_file_path = os.path.join(script_dir, compList)
    with open(abs_file_path, 'w') as fp:
        json.dump(stockList, fp, indent=4)
    # write companyData
    compData = '{}/stockData.json'.format(dirName, suffix)
    abs_file_path = os.path.join(script_dir, compData)
    with open(abs_file_path, 'w') as fp:
        json.dump(scraped_data, fp, indent=4)


def emailStats(stockList=None, scraped_data=None):
    doDiff()
    print('todo')


if __name__ == "__main__":
    parser = ap.ArgumentParser(description="My Script")
    # parser.add_argument("--myArg")
    parser.add_argument('-l', '--list', nargs='+', help='<Required> Set flag', required=False)
    args, leftovers = parser.parse_known_args()

    inputExist = False
    for _, stockSet in parser.parse_args()._get_kwargs():
        if stockSet is not None:
            print("getting stats for the stockList stock and writing result!")
            inputExist = True
            stockList, scraped_data = stockGetStats(stockSet)
            writeStats(stockList, scraped_data, '_custom')
            emailStats(stockList, scraped_data)

    if not inputExist:
        # check if already exist
        dateStamp = datetime.datetime.now().strftime("%Y-%m-%d")
        # script_dir = os.path.dirname(__file__)
        # abs_path = os.path.join(script_dir, dateStamp)
        # if not os.path.isdir(abs_path):
        # not existed
        if not os.path.isdir('./' + dateStamp):
            print('existed')
            print("screening stock and writing result!")
            stockList, scraped_data = stockScreen()
            writeStats(stockList, scraped_data)
            emailStats(stockList, scraped_data)
        emailStats()
