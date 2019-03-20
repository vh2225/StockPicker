import argparse as ap
import datetime
import json
import os

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


def writeStats(stockList, scraped_data):
    dateStamp = datetime.datetime.now().strftime("%Y-%m-%d")
    os.makedirs(dateStamp, exist_ok=True)
    script_dir = os.path.dirname(__file__)  # <-- absolute dir the script is in
    # write companyList
    compList = "{}/stockList.json".format(dateStamp)
    abs_file_path = os.path.join(script_dir, compList)
    with open(abs_file_path, 'w') as fp:
        json.dump(stockList, fp, indent=4)
    # write companyData
    compData = '{}/stockData.json'.format(dateStamp)
    abs_file_path = os.path.join(script_dir, compData)
    with open(abs_file_path, 'w') as fp:
        json.dump(scraped_data, fp, indent=4)


def emailStats(stockList, scraped_data):
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
            writeStats(stockList, scraped_data)
            emailStats(stockList, scraped_data)

    if not inputExist:
        print("screening stock and writing result!")
        stockList, scraped_data = stockScreen()
        writeStats(stockList, scraped_data)
        emailStats(stockList, scraped_data)
