##!#/usr/bin/env python3

import os
import sys
import argparse
import pygtrie
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

# Debugging Mode?
debug = True

# Set up argument parser
parser = argparse.ArgumentParser(description='Search motorcycles all over the US', prefix_chars='-')
parser.add_argument('-s', '--search',
                    help='term you want to search')
parser.add_argument('-max', '--max_price')
parser.add_argument('-i', '--ignore',  help='ignore results with these words in them (separated by comma (,) no spaces)')
args = parser.parse_args()

# Define search region dictionary for CLI user input
regions = {}
regions[('nyc', 'ny', 'new york', 'newyork')] = 'newyork'
regions[('long island', 'li', 'longisland')] = 'longisland'
regions[('hv', 'hudsonvalley', 'hudson valley')] = 'hudsonvalley'
regions[('jersey', 'north jersey', 'northjersey', 'nj', 'new jersey', 'newjersey')] = 'newjersey'
regions[('san fransisco', 'sf', 'sanfransisco', 'sfbay')] = 'sfbay'
regions[('birmingham', 'bham')] = 'bham'
regions[('atl', 'atlanta')] = 'atlanta'
regions[('auburn', 'aub', 'au')] = 'auburn'
regions[('phili', 'philadelphia')] = 'philadelphia'
regions[('boston')] = 'boston'
regions[('dc', 'washdc', 'washingtondc')] = 'washingtondc'



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
neighborhoods = []

# Set up Google Sheets interface
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('find-motorcycles.json', scope)
gc = gspread.authorize(credentials)
wks = gc.open("find-motorcycles").sheet1
ss_key = '1vm_Op7XRmtHIuF8UX_B7vbatS_MPnOj5gPCv0JWy-Y0'
wks_name = 'find-motorcycles'

# Optional
try:
    region_input = input('Enter cities you want craigslist to search (no spaces) separated by ",": ').lower().split(',')
except:
    pass

if debug == True:
    print('city input: ', region_input)
    print('length of city input: ', len(region_input))
    print('byte size of city input: ', sys.getsizeof(region_input))
    # print(regions[(region_input.split(' '))])

# Cities actual name
city_names = ['atlanta', 'austin', 'boston', 'chicago', 'dallas', 'denver', 'detroit', 'houston', 'las vegas', 'los angeles', 'miami', 'minneapolis', 'new york', 'orange co', 'philadelphia', 'phoenix', 'portland', 'raleigh', 'sacramento', 'san diego', 'seattle', 'sf bayarea', 'wash dc']
# url prefix of major cities
city_codes = ['atlanta', 'austin', 'boston', 'chicago', 'dallas', 'denver', 'detroit', 'houston', 'lasvegas', 'losangeles', 'miami', 'minneapolis' ,'newyork', 'orangecounty', 'philadelphia', 'phoenix', 'portland', 'raleigh', 'sacramento', 'sandiego', 'seattle', 'sfbay', 'washingtondc']

#TODO: refactor. refactor. refactor.

# Main scrape function
def scrape(search_regions):

    # Set search parameters
    if args.search:
        query = args.search.replace(',', '%20')
    else:
        query = ''
    if args.max_price:
        max_price = args.max_price
    else:
        max_price = ''
    min_price = '500'
    search_type = 'T'   # T = search titles only
    has_pic = '1'       # 1 = must include picture
    search_nearby = '0'
    search_distance = '200'     # search x mile radius from specified zip
    postal = '11211'
    min_cc = ''
    max_cc = ''
    page = 0
    city_urls = []
    urls = []
    craigslist = 'http://craigslist.org'
    # state_pattern = re.compile(r'(?<=">")(.*)(?=</)')   # finds state inside url

    # Cities actual name
    city_names = ['atlanta', 'austin', 'boston', 'chicago', 'dallas', 'denver', 'detroit', 'houston', 'las vegas', 'los angeles', 'miami', 'minneapolis', 'new york', 'orange co', 'philadelphia', 'phoenix', 'portland', 'raleigh', 'sacramento', 'san diego', 'seattle', 'sf bayarea', 'wash dc']
    # url prefix of major cities
    city_codes = ['atlanta', 'austin', 'boston', 'chicago', 'dallas', 'denver', 'detroit', 'houston', 'lasvegas', 'losangeles', 'miami', 'minneapolis' ,'newyork', 'orangecounty', 'philadelphia', 'phoenix', 'portland', 'raleigh', 'sacramento', 'sandiego', 'seattle', 'sfbay', 'washingtondc']


    for region in search_regions:
        # Reset page number for next city
        page = 0

        # Keep looping as long as a next page is detected
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

            # Access page of each listing
            for url in link_html:
                link = url.get('href')  # grab url inside of a-tag
                links.append(link)

                cities.append(region)

                # Grab html of individual results
                with requests.Session() as session:
                    print('\nmaking item request...\n')
                    res = session.get(link)
                    spans = BeautifulSoup(res.content, 'lxml', parse_only=SoupStrainer('span'))
                    p_tags = BeautifulSoup(res.content, 'lxml', parse_only=SoupStrainer('p'))

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

                # Collect Title
                title_html = spans.find_all('span', {'id': 'titletextonly'})
                for i in title_html:
                    title = i.text
                    title = ''.join(title) # list by default / convert to string
                    titles.append(title)
                    # print('title: ', titles[-1])

                # Collect neighborhood if provided
                try:
                    neighborhoods.append(spans.find_all('small')[0].text.lstrip(' (').rstrip(')'))
                except:
                    neighborhoods.append('N/A')

                if debug == True:
                    print('neighborhood: ', neighborhoods[-1])

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

                if debug == True:
                    print('year: ', year[-1])
                    print('make: ', make[-1])
                    print('model: ', model[-1])

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

                if debug == True:
                    print('miles = ', miles[-1])

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

                if debug == True:
                    print('displacement = ', ccs[-1])

            # Determine if there is a next page
            next_button = []
            for n in next_html:
                next_button = n.get('href')

            if len(next_button) > 0:    # if there is an href in next button html then there is another page. CL pages are notated in intervals of 120
                page = page + 120
            else:
                break

# Search entire country
if sys.getsizeof(region_input) <= 72:
    search_regions = city_codes

    if debug == True:
        print('\nsearching entire U.S.\n')

    # Perform search on each city in the nation
    scrape(search_regions)

# Only search pre-selected regions
else:
    search_regions = []
    for i in regions:
        if any(x in i for x in region_input):
            search_regions.append(regions[i])
            print('\nSearching '+ regions[i])
    scrape(search_regions)

# Debugging
if debug == True:
    print('\nprices: ')
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
    print('neighborhoods: ', len(neighborhoods))
    print('title: ', len(titles))

# Add results to dataframe
try:
    df = pd.DataFrame({'Price': prices, 'City': cities, 'Year': year, 'Mileage': miles, 'Engine Size': ccs, 'Make': make, 'Model': model, 'Title': titles, 'Neighborhood': neighborhoods, 'Link': links})
    pd.set_option("display.max_colwidth", 10000)
except:
    print('Could not add results to dataframe')

if debug == True:
    print('\nFiltering unwanted keywords...\n')
    print('\ndf: ', df)

# Finer filter: exclude listings with these words
if args.ignore == 'default':
    ignore = ['parts', 'tank', 'motor', 'engine', 'tow', 'tag', 'dirt', 'chopper',  'wanted', 'manual', 'finance', 'approved', 'zero', 'financing', 'atv', '50', 'scooter', 'single-cylinder', 'can-am', 'ryker', 'spyder', 'camper', 'lineup']
    for i in ignore:
        print('ignore default: ', i)
elif args.ignore:
    ignore = args.ignore.split(',')
    if debug == True:
        for i in ignore:
            print('ignore: ', i)
    df = df[~df.Title.astype(str).str.contains(i)].sort_values('Price').drop_duplicates()

# >>> For checking if new listings exist <<<
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

if debug == True:
    print('\ndf: \n', df)
    print('\nupdated: \n', updated)
    print('\nss_key: ', ss_key)
    print('\nwks_name: ', wks_name)
    print('\ncredentials: ', credentials)

# Send dataframe to google sheets
print('\nSending filtered results to google sheets at https://docs.google.com/spreadsheets/d/1vm_Op7XRmtHIuF8UX_B7vbatS_MPnOj5gPCv0JWy-Y0/edit#gid=0')

d2g.upload(updated, ss_key, wks_name, credentials=credentials, row_names=True)

# df.to_csv(filepath, index=False)

print('\n\nsuccess\n')