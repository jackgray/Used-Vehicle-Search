
regions = {}

regions[('nyc', 'newyork')] = 'newyork'
regions[('long island', 'li', 'longisland')] = 'longisland'
regions[('hudsonvalley', 'hudson valley')] = 'hudsonvalley'
regions[('jersey', 'north jersey', 'northjersey', 'nj', 'new jersey', 'newjersey')] = 'newjersey'
regions[('san fransisco', 'sf', 'sanfransisco', 'sfbay')] = 'sfbay'
regions[('birmingham', 'bham')] = 'bham'

# region_input = ['san fransisco', 'nyc']
region_input = tuple(input('Enter cities you want craigslist to search (separated by comma-space (", "): ').lower().split(', '))

for i in region_input:
    print(i)
search_regions = []
# region_input=('sf', 'nyc')
# region_input=tuple(region_input.split(','))

for i in regions:
    if any(x in i for x in region_input):
        search_regions.append(regions[i])

```>>> input: 'sf', 'nyc', 'new jersey'
>>> return: 'sfbay', 'newyork', 'newjersey'```