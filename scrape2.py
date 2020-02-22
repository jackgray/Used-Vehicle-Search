# Perform search on each city listed in argument
    for region in search_regions:
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

                 cities.append(region)

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
                    locales.append(spans.find_all('small')[0].text.lstrip(' (').rstrip(')'))
                except:
                    locales.append('N/A')
                # print('locale: ', locales[-1])

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