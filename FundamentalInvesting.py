import re
import urllib
import urllib.request
from lxml import html
import requests
# from time import sleep
import json
# import argparse
from collections import OrderedDict
from time import sleep
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

regexMask = {
    'price Book Ratio': 'Price\/Book.*?data\-reactid.*?>(\d+\.\d*)</td>',
    'PEG Ratio 5y': 'PEG\sRatio.*?data\-reactid.*?>(\d+\.\d*)</td>'
}


def yahooRequest(stock):
    try:
        url = 'https://finance.yahoo.com/quote/{}/key-statistics?ltr=1'.format(stock)
        # print('url: ' + url)
        response = urllib.request.urlopen(url)
        html = str(response.read())
        return html

    except Exception as e:
        print('failed in the main loop of yahooKeyStats' + str(e))


def yahooStats(html, stat):
    try:
        # statVal = re.search(regexMask[stat] + '.*?data\-reactid.*?>(\d+\.\d*)</td>', html).group(1)
        statVal = re.search(regexMask[stat], html).group(1)
        return statVal

    except Exception as e:
        print('failed in the main loop of yahooKeyStats' + str(e))


def yahooParse(ticker):
    url = "http://finance.yahoo.com/quote/%s?p=%s" % (ticker, ticker)
    response = requests.get(url, verify=False)
    print("Parsing %s" % (url))
    sleep(4)
    parser = html.fromstring(response.text)
    summary_table = parser.xpath('//div[contains(@data-test,"summary-table")]//tr')
    summary_data = OrderedDict()
    other_details_json_link = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{0}?formatted=true&lang=en-US&region=US&modules=summaryProfile%2CfinancialData%2CrecommendationTrend%2CupgradeDowngradeHistory%2Cearnings%2CdefaultKeyStatistics%2CcalendarEvents&corsDomain=finance.yahoo.com".format(
        ticker)
    summary_json_response = requests.get(other_details_json_link)
    try:
        json_loaded_summary = json.loads(summary_json_response.text)
        y_Target_Est = json_loaded_summary["quoteSummary"]["result"][0]["financialData"]["targetMeanPrice"]['raw']
        earnings_list = json_loaded_summary["quoteSummary"]["result"][0]["calendarEvents"]['earnings']
        eps = json_loaded_summary["quoteSummary"]["result"][0]["defaultKeyStatistics"]["trailingEps"]['raw']
        datelist = []
        for i in earnings_list['earningsDate']:
            datelist.append(i['fmt'])
        earnings_date = ' to '.join(datelist)
        for table_data in summary_table:
            raw_table_key = table_data.xpath('.//td[contains(@class,"C(black)")]//text()')
            raw_table_value = table_data.xpath('.//td[contains(@class,"Ta(end)")]//text()')
            table_key = ''.join(raw_table_key).strip()
            table_value = ''.join(raw_table_value).strip()
            summary_data.update({table_key: table_value})
        summary_data.update(
            {'1y Target Est': y_Target_Est, 'EPS (TTM)': eps, 'Earnings Date': earnings_date, 'ticker': ticker,
             'url': url})
        return summary_data
    except:
        print("Failed to parse json response")
        return {"error": "Failed to parse json response"}


def finviz():
    try:
        stockSet = set()
        page = 0;
        while True:
            url = 'https://finviz.com/screener.ashx?v=111&f=cap_smallover,fa_curratio_o1.5,fa_ltdebteq_u0.3,fa_pb_u2,fa_pe_u20,sh_insiderown_o10&ft=4&o=ticker&r={}'.format(
                str(page * 20 + 1))
            # url = 'https://finviz.com/screener.ashx?v=111&f=fa_curratio_o1.5,fa_ltdebteq_u0.3,fa_pb_u2,fa_pe_u20,sh_insiderown_o10&ft=4&o=ticker&r={}'.format(str(page * 20 + 1))
            page += 1
            # print('url: ' + url)
            response = urllib.request.urlopen(url)
            html = str(response.read())
            # print(html)
            regex = 'href=\"quote\.ashx\?t=([a-zA-Z]+)\&ty=c&p=d&b=1\" class=\"screener-link-primary'
            stocks = re.findall(regex, html)
            # print(stocks)
            if any(stock in stockSet for stock in stocks):
                break
            stockSet.update(stocks)

        return stockSet

    except Exception as e:
        print('failed in the main loop of finviz' + str(e))


if __name__ == "__main__":
    # argparser = argparse.ArgumentParser()
    # argparser.add_argument('ticker', help='')
    # args = argparser.parse_args()
    stockSet = finviz()
    for ticker in stockSet:
        print("Fetching data for %s" % (ticker))
        scraped_data = yahooParse(ticker)
        print("Writing data to output file")
        with open('%s-summary.json' % (ticker), 'w') as fp:
            json.dump(scraped_data, fp, indent=4)

#
#
#
# label = 'ticker, '
# for stat in sorted(regexMask):
#     label += stat + ', '
# print(label)
#
# for ticker in stockSet:
#     # output = ticker + ', '
#     # response = yahooRequest(ticker)
#     # for stat in sorted(regexMask):
#     #     output += yahooStats(response, stat) + ', '
#     # print(output)
#     print(yahooParse(ticker))

# TODO: 1. extra filter: filter out the set with the following parameters:
#       PE 5y < 20
#       Growth rate: revenue, EPS, or net income >= 5-6%
#       margin of safety > 30%
#

# TODO: 2. report: email the ticker with the following parameters:
#         - Symbol
#         - Name
#         - Exchange
#         - Price & Value: EV, Price & Market cap -> (analyst) target price, price expected growth, STM reversal, LTM reversal
#         - 52w low/high
#         - Valuation ratios (intrinsic Val): all price/IV val% dif, margin of safety
#         - Valuation ratios (yield): price/eps (b, 5y), PEG Ratio
#         - Valuation ratios (Balance): price/book
#         - Liquidity ratios: current ratio
#         - Solvency ratios: LT Debt/Equity, Net debt/equity, FCF/LT Debt
#         - Shares: held by insiders, held by institutions
#         - Income: dividend (per share, 1y growth, 5y CAGR)
