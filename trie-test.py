import pygtrie

t = pygtrie.StringTrie()
t['nyc/newyork'] = 'newyork'
t['newjersey/jersey/nj'] = 'newjersey'

search_input = input('Enter regions to search: ' )

for i in t.items():
    print(i)
# for i in search_input:
#     print(t.__getitem__(i))

# print(t.__getitems__(search_input))

print(sorted(t['newjersey']))