import argparse as ap
import datetime
import json
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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
    diff = {'+': [], '-': []}
    for stock in new:
        if stock not in old:
            diff['+'].append(stock)

    for stock in old:
        if stock not in new:
            diff['-'].append(stock)

    with open('diff.txt', 'w') as fp:
        json.dump(diff, fp, indent=4)

    return json.dumps(diff)


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


def emailStats(diff, stockList=None, scraped_data=None):
    # pithonstork@gmail.com
    gmailUser = 'pithonstork@gmail.com'
    gmailPassword = '5252025$'
    recipients = ['yangtze87@yahoo.com', 'yangtze87@gmail.com', 'xiongchuanxi@gmail.com']
    message = '' + diff + '\n'
    if stockList:
        message += 'stockList:' + '\n'
        message += json.dumps(stockList, sort_keys=True, indent=4) + '\n'

    if scraped_data:
        message += 'scraped_data:' + '\n'
        message += json.dumps(scraped_data, sort_keys=True, indent=4) + '\n'

    msg = MIMEMultipart()
    msg['From'] = gmailUser
    msg['Subject'] = "stock screening result"
    msg.attach(MIMEText(message))

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
            writeStats(stockList, scraped_data, '_custom')
            emailStats(stockList, scraped_data)

    if not inputExist:
        # check if already exist
        dateStamp = datetime.datetime.now().strftime("%Y-%m-%d")
        if not os.path.isdir('./' + dateStamp):
            print("screening stock and writing result!")
            stockList, scraped_data = stockScreen()
            diff = doDiff(stockList)
            writeStats(stockList, scraped_data)
            emailStats(diff, stockList, scraped_data)
