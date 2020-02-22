from lxml import html
from bs4 import BeautifulSoup
from bs4 import SoupStrainer
import requests
import sys
import os

city_urls=[]
cities=[]
city_codes=[]
with requests.Session() as session:
        res = session.get('http://craigslist.com')
        html = BeautifulSoup(res.content, 'lxml')
        cities_html = html.find_all('ul', {'class': 'menu collapsible'})
for i in cities_html:
    city_atags = i.find_all('ul', {'class': 'acitem'})[1].find_all('a')
for i in city_atags:
    city_url = i.get('href')
    cities.append('\'' + i.text + '\'')
    city_codes.append(city_url.replace('http://', "'").replace('.craigslist.org', "\'"))
cities.pop(-1)
city_codes.pop(-1)

with open('city_names.txt', 'w') as city_names:
    city_names.write(', '.join(map(str, cities)))

with open('city_codes.txt', 'w') as codes:
    codes.write(', '.join(map(str, city_codes)))