##!#/usr/bin/env python3

import os
import sys
import argparse
from lxml import html
from bs4 import BeautifulSoup
from bs4 import SoupStrainer
from email.message import EmailMessage
import requests
import re
import numpy as np
import pandas as pd
import smtplib, ssl
import gspread
from df2gspread import df2gspread as d2g
from oauth2client.service_account import ServiceAccountCredentials

# Set up argument parser
parser = argparse.ArgumentParser(description='Search motorcycles all over the US')
parser.add_argument('search',
                    help='term you want to search')
parser.add_argument('max_price')
args = parser.parse_args()

# Set up Google Sheets interface
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('find-motorcycles.json', scope)
gc = gspread.authorize(credentials)
wks = gc.open("find-motorcycles").sheet1
ss_key = '1vm_Op7XRmtHIuF8UX_B7vbatS_MPnOj5gPCv0JWy-Y0'
wks_name = 'find-motorcycles'

# Set up Pandas data frame
ccs = []
prices = []
titles = []
links = []
miles = []
model = []
year = []
make = []
cities = []
locations = []

# Set search parameters
search_nation = 'yes'
query = args.search
max_price = args.max_price
min_price = '500'
search_type = 'T'   # T = search titles only
has_pic = '1'       # 1 = must include picture
search_nearby = '0'
search_distance = '200'     # search x mile radius from specified zip
postal = '11211'
min_cc = ''
max_cc = ''
query = query.replace(' ', '%20')
pages = ['', '120', '240', '360', '480', '600', '720', '840']
page = 0

city_urls = []
urls = []
search_regions = ['newyork', 'newjersey']
craigslist = 'http://craigslist.com'
state_pattern = re.compile(r'(?<=">")(.*)(?=</)')   # finds state inside url

#TODO: refactor. refactor. refactor.

if search_nation == 'yes':
    # Get list of regions for searching entire US
    with requests.Session() as session:
        res = session.get(craigslist)
        html = BeautifulSoup(res.content, 'lxml')
        regions_html = html.find_all('ul', {'class': 'menu collapsible'})
        with open('regions.txt', 'w') as regions:
            regions.write('\n'.join(map(str, regions_html)))
        for i in regions_html:
            cities_html = i.find_all('ul', {'class': 'acitem'})[1].find_all('a')
        for i in cities_html:
            city_urls.append(i.get('href'))
        city_urls.pop(-1)   # last url scraped is bunk -- remove it

    # Perform search on each city in the nation
    for city_url in city_urls:
        page = 0
        while True:
            # Collect individual links from query results
            url = city_url + 'search/mca?s=' + str(page) + '&query=' +  query + '&srchType=' + search_type + '&hasPic=' + has_pic + '&min_price=' + min_price + '&max_price=' + max_price

            # Grab results page
            with requests.Session() as session:
                res = session.get(url)
                html = BeautifulSoup(res.content, 'lxml')

            # Grab all a-tags (listing links)
            link_html = html.find_all('a', {'class': 'result-title hdrlnk'})

            # Next page of results exists if there is an a-tag with class "button next"
            next_html = html.find_all('a', {'class': 'button next'})

            # Access page of individual results
            for url in link_html:
                link = url.get('href')  # grabs url inside of a-tag
                links.append(link)

                # Save city from url prefix
                city = city_url.replace('http://', '').replace('.craigslist.org/', '')
                cities.append(city)

                # Grab html of individual results
                with requests.Session() as session:
                    print('\nmaking item request...\n')
                    res = session.get(link)
                    spans = BeautifulSoup(res.content, 'lxml', parse_only=SoupStrainer('span'))
                    p_tags = BeautifulSoup(res.content, 'lxml', parse_only=SoupStrainer('p'))

                # print('link: ', links[-1])
                # print('city: ', cities[-1])

                # Collect price
                price_html = spans.find_all('span', {'class': 'price'})
                for i in price_html:
                    try:
                        price = int(i.contents[0].string.strip('$'))
                    except:
                        price = 'N/A'
                if price:
                    prices.append(price)
                else:
                    prices.append('N/A')

                # print('price:', prices[-1])

                # Collect Title
                title_html = spans.find_all('span', {'id': 'titletextonly'})
                for i in title_html:
                    title = i.text
                    title = ''.join(title) # list by default / convert to string
                    titles.append(title)
                    # print('title: ', titles[-1])

                # Collect location
                try:
                    locations.append(spans.find_all('small')[0].text.lstrip(' (').rstrip(')'))
                except:
                    locations.append('N/A')
                # print('locale: ', locations[-1])

                # Find vehicle name info
                name_html = p_tags.find_all('p', {'class': 'attrgroup'})
                if name_html:
                    name = name_html[0].find_next('b').text.lstrip(' ')
                    name = name.split(' ')  # parse name into components
                    # Vehicle name section is unformated--could include any combination of year/make/model/engine size
                    # Determine if year is included in vehicle name
                    if len(name[0]) > 4:    # year is 4 chars; if first item is more than that then assume the date is not given and that the first item is
                        try:
                            make.append(name[0])
                            year.append('N/A')      # assume year not given
                        except:
                            make.append('N/A')
                        try:
                            model.append(' '.join(name[1:])) # rest of the words probably belong to the model
                        except:
                            model.append('N/A')
                    else:
                        try:
                            make.append(name[1])    # typical order is year, make, model, engine size
                        except:
                            make.append('N/A')
                        try:
                            model.append(' '.join(name[2:]))
                        except:
                            model.append('N/A')
                        try:
                            year.append(name[0])    # 4 or less chars in first word probably is the date
                        except:
                            year.append('N/A')
                else:
                    model.append('N/A')
                    year.append('N/A')
                    make.append('N/A')

                # print('year: ', year[-1])
                # print('make: ', make[-1])
                # print('model: ', model[-1])

                # Collect miles
                odom_html = spans.find_all(text=re.compile('odometer:'))
                # First determine if poster specified mileage
                if odom_html:
                    for i in odom_html:
                        try:
                            miles.append(i.find_next('b').text)
                        except:
                            miles.append('N/A')
                else:
                    miles.append('N/A')
                # print('miles = ', miles[-1])

                # Collect engine size
                cc_html = spans.find_all(text=re.compile('engine displacement \(CC\)'))
                # First determine if poster specified engine size
                if cc_html:
                    for i in cc_html:
                        try:
                            ccs.append(i.find_next('b').text)
                        except:
                            ccs.append('N/A')
                else:
                    ccs.append('N/A')
                # print('displacement = ', ccs[-1])

            # Determine if there is a next page
            next_button = []
            for n in next_html:
                next_button = n.get('href')

            if len(next_button) > 0:    # if there is an href in next button html then there is another page. CL pages are notated in intervals of 120
                page = page + 120
            else:
                break

# Only search pre-selected regions
if search_nation == 'no':

    # Perform search on each city listed in argument
    for region in search regions:
        # reset page number
        page = 0
        # keep looping as long as a next page is detected
        while True:
            # Collect individual links from query results
            url = 'http://' + region +  '.craigslist.org/search/mca?s=' + str(page) + '&query=' +  query + '&srchType=' + search_type + '&hasPic=' + has_pic + '&min_price=' + min_price + '&max_price=' + max_price

            # Grab results page
            with requests.Session() as session:
                res = session.get(url)
                html = BeautifulSoup(res.content, 'lxml')

            # Grab all a-tags (listing links)
            link_html = html.find_all('a', {'class': 'result-title hdrlnk'})

            # Next page of results exists if there is an a-tag with class "button next"
            next_html = html.find_all('a', {'class': 'button next'})

            # Access page of individual results
            for url in link_html:
                link = url.get('href')  # grabs url inside of a-tag
                links.append(link)

                # Save city from url prefix
                city = city_url.replace('http://', '').replace('.craigslist.org/', '')
                cities.append(city)

                # Grab html of individual results
                with requests.Session() as session:
                    print('\nmaking item request...\n')
                    res = session.get(link)
                    spans = BeautifulSoup(res.content, 'lxml', parse_only=SoupStrainer('span'))
                    p_tags = BeautifulSoup(res.content, 'lxml', parse_only=SoupStrainer('p'))

                # print('link: ', links[-1])
                # print('city: ', cities[-1])

                # Collect price
                price_html = spans.find_all('span', {'class': 'price'})
                for i in price_html:
                    try:
                        price = int(i.contents[0].string.strip('$'))
                    except:
                        price = 'N/A'
                if price:
                    prices.append(price)
                else:
                    prices.append('N/A')

                # print('price:', prices[-1])

                # Collect Title
                title_html = spans.find_all('span', {'id': 'titletextonly'})
                for i in title_html:
                    title = i.text
                    title = ''.join(title) # list by default / convert to string
                    titles.append(title)
                    # print('title: ', titles[-1])

                # Collect location
                try:
                    locations.append(spans.find_all('small')[0].text.lstrip(' (').rstrip(')'))
                except:
                    locations.append('N/A')
                # print('locale: ', locations[-1])

                # Find vehicle name info
                name_html = p_tags.find_all('p', {'class': 'attrgroup'})
                if name_html:
                    name = name_html[0].find_next('b').text.lstrip(' ')
                    name = name.split(' ')  # parse name into components
                    # Vehicle name section is unformated--could include any combination of year/make/model/engine size
                    # Determine if year is included in vehicle name
                    if len(name[0]) > 4:    # year is 4 chars; if first item is more than that then assume the date is not given and that the first item is
                        try:
                            make.append(name[0])
                            year.append('N/A')      # assume year not given
                        except:
                            make.append('N/A')
                        try:
                            model.append(' '.join(name[1:])) # rest of the words probably belong to the model
                        except:
                            model.append('N/A')
                    else:
                        try:
                            make.append(name[1])    # typical order is year, make, model, engine size
                        except:
                            make.append('N/A')
                        try:
                            model.append(' '.join(name[2:]))
                        except:
                            model.append('N/A')
                        try:
                            year.append(name[0])    # 4 or less chars in first word probably is the date
                        except:
                            year.append('N/A')
                else:
                    model.append('N/A')
                    year.append('N/A')
                    make.append('N/A')

                # print('year: ', year[-1])
                # print('make: ', make[-1])
                # print('model: ', model[-1])

                # Collect miles
                odom_html = spans.find_all(text=re.compile('odometer:'))
                # First determine if poster specified mileage
                if odom_html:
                    for i in odom_html:
                        try:
                            miles.append(i.find_next('b').text)
                        except:
                            miles.append('N/A')
                else:
                    miles.append('N/A')
                # print('miles = ', miles[-1])

                # Collect engine size
                cc_html = spans.find_all(text=re.compile('engine displacement \(CC\)'))
                # First determine if poster specified engine size
                if cc_html:
                    for i in cc_html:
                        try:
                            ccs.append(i.find_next('b').text)
                        except:
                            ccs.append('N/A')
                else:
                    ccs.append('N/A')
                # print('displacement = ', ccs[-1])

            # Determine if there is a next page
            next_button = []
            for n in next_html:
                next_button = n.get('href')

            if len(next_button) > 0:    # if there is an href in next button html then there is another page. CL pages are notated in intervals of 120
                page = page + 120
            else:
                break


print('prices: ')
count = 0
for i in prices:
    count = count + 1
    print(count, ' ', i)
print('year: ')
count = 0
for i in year:
    count = count + 1
    print(count, ' ', i)
count = 0
print('titles: ')
for i in titles:
    count = count + 1
    print(count, ' ', i)
print('miles: ')
count = 0
for i in miles:
    count = count + 1
    print(count, ' ', i)
count = 0
print(len(links))
print('links: ')
for i in links:
    count = count + 1
    print(count, ' ', i)
print('ccs: ')
count = 0
for i in ccs:
    count = count + 1
    print(count, ' ', i)
print('model: ')
count=0
for i in model:
    count = count + 1
    print(count, ' ', i)
print('price: ', len(prices))
print('city: ', len(cities))
print('year: ', len(year))
print('miles: ', len(miles))
print('ccs: ', len(ccs))
print('model: ', len(model))
print('make: ', len(make))
print('locale: ', len(locations))
print('title: ', len(titles))

# Add results to dataframe
df = pd.DataFrame({'Price': prices, 'City': cities, 'Year': year, 'Mileage': miles, 'Engine Size': ccs, 'Make': make, 'Model': model, 'Title': titles, 'Locale': locations, 'Link': links})
pd.set_option("display.max_colwidth", 10000)


ignore = ['parts', 'grom', 'tank', 'motor', 'scooter', 'vespa', 'engine', 'shadow', 'tow', 'tag', 'goldwing', 'dirt', 'ruckus', 'chopper', 'virago', 'wanted', 'moped', 'scooter', 'xr', 'manual', 'cbr', 'crf', 'hondamatic', 'harley', '125', 'star', 'rebel', 'vulcan', 'cr', 'wr', 'car', 'finance', 'hyosung', 'approved', 'zero', 'financing', 'atv', 'sabre', '50', 'single-cylinder', 'can-am', 'ryker', 'spyder', 'camper', 'lineup']
# df = df[df.Title.str.contains('honda cb|yamaha sr')].sort_values('Price')

# print('\nFiltering unwanted keywords...\n')
if args.ignore:
    for i in ignore:
        df = df[~df.Title.str.contains(i)].sort_values('Price').drop_duplicates()

# print(newdf)
# Max Price
# newdf = df[(df.Price == 0) | ((df.Price < max_price) & (df.Price > min_price))].sort_values('Price').drop_duplicates()
# Min Price
#newdf = df[df.Price > 500]     # Too many legit listings with $0
# print(df.to_string())

# Compare to last scan for new items
# filepath = '/Users/jackgray/Documents/cronjobs/find-motorcycles/output.txt'
# if os.stat(filepath).st_size > 0:
#     olddf = pd.read_csv(filepath)
#     # print(olddf.to_string())
# else:
#     olddf = pd.DataFrame({})

# df_concat = pd.concat([newdf, olddf], sort=True)

# diff_df = df_concat.drop_duplicates(keep=False)

# Send an email for new results

# if diff_df.empty == False:
#     # Set up email server
#     port = 465
#     password = '0xf0rdc0mm4s'
#     context = ssl.create_default_context()
#     smtp_server = 'smtp.gmail.com'
#     to_ = 'jgrayau@gmail.com'
#     from_ = 'jgrayau@gmail.com'
#     message = diff_df.to_string()
#     context = ssl.create_default_context()
#     subject = 'New Listings!'
#     fmt = 'From: {}\r\nTo: {}\r\nSubject: {}\r\n{}'
#     # Send dataframe as message
#     email = EmailMessage()
#     email.set_content(fmt.format(to_, from_, subject, message))
#     email['To'] = to_
#     email['From'] = from_
#     email['Subject'] = subject
#     with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
#         server.login(from_, password)
#         server.send_message(email)

    # with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
    #     server.login(sender_email, password)
    #     server.sendmail(sender_email, receiver_email, message, fmt.format(sender_email, receiver_email, subject, message).encode('utf-8'))

updated = df.drop_duplicates().sort_values('Price')

with open('results.txt', mode='w') as tmp:
    updated.to_csv(tmp, sep='\t', encoding='utf-8')

# Send dataframe to google sheets
print('\nSending filtered results to google sheets at https://docs.google.com/spreadsheets/d/1vm_Op7XRmtHIuF8UX_B7vbatS_MPnOj5gPCv0JWy-Y0/edit#gid=0')
d2g.upload(updated, ss_key, wks_name, credentials=credentials, row_names=True)


# df.to_csv(filepath, index=False)
