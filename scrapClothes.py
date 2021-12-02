from bs4 import BeautifulSoup
import requests
import csv
import os
import pandas as pd


# variables:
urlmain= "https://www.50languages.com/vocab/learn/en/hu/16/"

#Codes:
var = 1
while var > 0:
    html_text = requests.get(urlmain).text
    soup = BeautifulSoup(html_text, 'lxml')
    try:
        webdata = soup.find_all('div', class_='feature-box-info')
    except NameError:
        break
    else:
        hu_array = []
        eng_array =[]
        pics_array = []
        file_array =[]
        for webdatum in webdata:
            hungwords = webdatum.find('a').text
            hu_array.append(hungwords.replace(" ",""))
            engwords = webdatum.find('p', class_='mb-lg').text
            eng_array.append(engwords.replace(" ",""))
    var = var -1

    try:
        webdata = soup.find_all('img', class_='vocabimage')
    except NameError:
        break
    else:
        for webdatum in webdata:
            link= "https://www.50languages.com/vocab/" + webdatum.get('src')
            pics_array.append(link)
            name = webdatum.get('src').replace("images/","")
            file_array.append(name)
            with open(name, 'wb') as f:
                im = requests.get(link)
                f.write(im.content)
                print("writing: " + name)
            
                 
    data = {'Hungarian':hu_array,
            'English':eng_array,
            'Photos':file_array,
        }
    df = pd. DataFrame(data,columns=['Hungarian', 'English', 'Photos'])
    print(df.head())
    with open('new_vocab.csv','w') as result_file:
        wr = csv.writer(result_file, dialect='excel')
    new_vocab = df.to_csv('new_vocab.csv', index=False)
    print(new_vocab)

