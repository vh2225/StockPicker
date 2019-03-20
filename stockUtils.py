import json
import re
import urllib
import urllib.request
from collections import OrderedDict
from time import sleep

import requests
import urllib3
from lxml import html

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


def getStatsFromYahoo(ticker):
    url = "http://finance.yahoo.com/quote/%s?p=%s" % (ticker, ticker)
    response = requests.get(url, verify=False)
    # print("Parsing %s" % (url))
    sleep(4)
    parser = html.fromstring(response.text)
    summary_table = parser.xpath('//div[contains(@data-test,"summary-table")]//tr')
    summary_data = dict()
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
    except Exception as e:
        print("Failed to parse json response in getStatsFromYahoo: " + str(e))
        return {"error": "Failed to parse json response in getStatsFromYahoo" + str(e)}


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
def getStatsFromFMPrep(ticker):
    summary_data = dict()
    try:
        # get general info
        url = "https://financialmodelingprep.com/api/company/profile/{}".format(ticker)
        request = requests.get(url)
        summary_data.update(json.loads(request.text[5:-5])[ticker])
        # get ratings
        url = "https://financialmodelingprep.com/api/company/rating/{}".format(ticker)
        request = requests.get(url)
        summary_data.update(json.loads(request.text[5:-5])[ticker])
        # get intrinsic val
        url = "https://financialmodelingprep.com/api/company/discounted-cash-flow/{}".format(ticker)
        request = requests.get(url)
        summary_data.update(json.loads(request.text[5:-5])[ticker])
        marginOS = "{0:.2f}".format(((summary_data.get('DCF') - summary_data.get('Price'))
                                     * 100 / summary_data.get('Price'))) + '%'

        summary_data.update({'margin of safety': marginOS})
        return summary_data
    except Exception as e:
        print("Failed to parse json response in getStatsFromFMPrep: " + str(e))
        return {"error": "Failed to parse json response in getStatsFromFMPrep" + str(e)}


def getStat(ticker):
    summary_data = dict()
    summary_data.update(getStatsFromYahoo(ticker))
    summary_data.update(getStatsFromFMPrep(ticker))
    return OrderedDict(sorted(summary_data.items()))


def getStockFromFinviz():
    try:
        stockSet = set()
        page = 0;
        while True:
            url = 'https://finviz.com/screener.ashx?v=111&f=cap_smallover,fa_curratio_o1.5,fa_ltdebteq_u0.3,fa_pb_u2,fa_pe_u20,sh_insiderown_o10&ft=4&o=ticker&r={}'.format(
                str(page * 20 + 1))
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
