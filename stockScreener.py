import argparse as ap
import datetime
import json
import os
import re
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os.path import basename

import pandas as pd

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


def doDiff(stockList=None):
    regex = re.compile(r'\d+-\d+-\d+$')
    # get all dirs
    all_subdirs = sorted([d for d in os.listdir('.') if os.path.isdir(d) and regex.match(d)], reverse=True)
    if len(all_subdirs) == 0:
        return
    if stockList == None:
        if len(all_subdirs) < 2:
            return
        new = set(json.load(open(all_subdirs[0] + '/stockList.json')))
        old = set(json.load(open(all_subdirs[1] + '/stockList.json')))
    else:
        new = set(stockList)
        old = set(json.load(open(all_subdirs[0] + '/stockList.json')))
    diff = {'add': [], 'remove': []}
    for stock in new:
        if stock not in old:
            diff['add'].append(stock)

    for stock in old:
        if stock not in new:
            diff['remove'].append(stock)

    with open('diff.txt', 'w') as fp:
        json.dump(diff, fp, indent=4)

    return diff


def writeStats(stockList, scraped_data, suffix=''):
    dateStamp = datetime.datetime.now().strftime("%Y-%m-%d")
    dirName = '{}{}'.format(dateStamp, suffix)
    os.makedirs(dirName, exist_ok=True)
    script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in
    # write companyList
    compListFile = "{}/stockList.json".format(dirName, suffix)
    abs_file_path = os.path.join(script_dir, compListFile)
    with open(abs_file_path, 'w') as fp:
        json.dump(stockList, fp, indent=4)
    df = pd.DataFrame(scraped_data)
    df.set_index("ticker", inplace=True)
    df.transpose()
    stockDatacsv = '{}/stockData.csv'.format(dirName, suffix)
    df.to_csv(stockDatacsv, sep='\t')
    return stockDatacsv


def emailStats(diff=None, stockList=None, csv_file=None):
    # pithonstork@gmail.com
    gmailUser = 'pithonstork@gmail.com'
    gmailPassword = '5252025$'
    recipients = ['yangtze87@yahoo.com', 'yangtze87@gmail.com', 'xiongchuanxi@gmail.com']

    message = ''
    if diff:
        if diff['add']:
            message += 'stock(s) added to the recommendation list: ' + json.dumps(diff['add']) + '\n'
        if diff['remove']:
            message += 'stock(s) removed from the recommendation list: ' + json.dumps(diff['remove']) + '\n'
        if message == '':
            message += 'there is no change in the recommendation list from the last report \n'

    if not message == '':
        message += '\n'

    if stockList:
        if diff:
            message += 'recommended stocks:' + '\n'
        else:
            message += 'input stocks:' + '\n'
        message += json.dumps(stockList, sort_keys=True, indent=4) + '\n'

    msg = MIMEMultipart()
    msg['From'] = gmailUser
    msg['Subject'] = "πThon Stork delivers today stock recommendations"
    msg.attach(MIMEText(message))

    if csv_file:
        with open(csv_file, "rb") as fil:
            part = MIMEApplication(
                fil.read(),
                Name=basename(csv_file)
            )
        # After the file is closed
        part['Content-Disposition'] = 'attachment; filename="%s"' % basename(csv_file)
        msg.attach(part)

    mailServer = smtplib.SMTP('smtp.gmail.com', 587)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(gmailUser, gmailPassword)
    for recipient in recipients:
        msg['To'] = recipient
        mailServer.sendmail(gmailUser, recipient, msg.as_string())
    mailServer.close()


if __name__ == "__main__":
    parser = ap.ArgumentParser(description="My Script")
    parser.add_argument('-l', '--list', nargs='+', help='<Required> Set flag', required=False)
    args, leftovers = parser.parse_known_args()

    inputExist = False
    for _, stockSet in parser.parse_args()._get_kwargs():
        if stockSet is not None:
            print("getting stats for the stockList stock and writing result!")
            inputExist = True
            stockList, scraped_data = stockGetStats(stockSet)
            stockDatacsv = writeStats(stockList, scraped_data, '_custom')
            emailStats(None, stockList, stockDatacsv)

    if not inputExist:
        # check if already exist
        dateStamp = datetime.datetime.now().strftime("%Y-%m-%d")
        if not os.path.isdir('./' + dateStamp):
            print("screening stock and writing result!")
            stockList, scraped_data = stockScreen()
            diff = doDiff(stockList)
            stockDatacsv = writeStats(stockList, scraped_data)
            emailStats(diff, stockList, stockDatacsv)
