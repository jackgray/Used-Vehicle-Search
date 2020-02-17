from lxml import html
from bs4 import BeautifulSoup
from bs4 import SoupStrainer
import requests
import re
from pprint import pprint

with requests.Session() as session:
    res = session.get('https://atlanta.craigslist.org/atl/mcy/d/covington-honda-cbr-rr/7062741105.html')
    html = BeautifulSoup(res.content, 'html.parser', parse_only=SoupStrainer('span'))

# pprint(vars(html))
# # print(html, ' \n')
# html2 = html.find_all('p', {'class': 'attrgroup'})
# # print(html2.type())
# html2 = ' '.join(str(i) for i in html2)
# # print(html2)
# # print('\n\n\n')
odom_html = html.find_all(text=re.compile('odometer:'))

# print(odom_html)
if  odom_html:
    for i in odom_html:
        odom = i.find_next('b').text
    print(odom)
else:
    print('na')
# odom_html = odom_html[1]
# print(odom_html)
# for i in odom_html:
#     print(i.find_all(text=re.compile('odometer')))
# print(odom)
    # for j in i.find(text=re.compile("fuel: ")):
    #     if 'odometer' in j:
    #         print(j)
    # # print(i.find_all(contents=re.compile("^odom")))