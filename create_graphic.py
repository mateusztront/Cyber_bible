import eel
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import copy
import os
from functools import reduce
from draw_posts import draw_text, draw_text_pagination_first, draw_text_pagination_second

@eel.expose
def draw_post(thedate, verse_break):
    verse_break = int(verse_break)
    URL = f"https://liturgia.wiara.pl/kalendarz/67b53.Czytania-mszalne/{str(thedate)}"

    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    content_list = soup.find_all("div", "txt__rich-area")[1].get_text().split('\n')
    if content_list[-1] == '':
        del content_list[-1]

    if 'EWANGELIA DŁUŻSZA' in content_list:
        cut_points = ['PIERWSZE CZYTANIE', 'PSALM RESPONSORYJNY', 'DRUGIE CZYTANIE', 'EWANGELIA DŁUŻSZA', 'EWANGELIA KRÓTSZA']
    elif 'DRUGIE CZYTANIE' in content_list:
        cut_points = ['PIERWSZE CZYTANIE', 'PSALM RESPONSORYJNY', 'DRUGIE CZYTANIE', 'EWANGELIA']
    else:
        cut_points = ['PIERWSZE CZYTANIE', 'PSALM RESPONSORYJNY', 'EWANGELIA']

    content_dic = {}
    staging_list = [] 

    for text in content_list:
        if 'Liturgia Słowa' in text or '' == text:
            continue
            
        if text in cut_points:

            for text in content_list[content_list.index(text)+1:]:
                if text == '':
                    continue
                if text == 'albo':
                    content_dic[cut_points[0]] = staging_list
                    staging_list = [] 
                    del cut_points[0]
                    break    

                if text not in cut_points:
                    staging_list.append(text)
                    
                else:
                    content_dic[cut_points[0]] = staging_list
                    staging_list = [] 
                    del cut_points[0]
                    break
            
            content_dic[cut_points[0]] = staging_list

    content_dic 

    if 'EWANGELIA KRÓTSZA' in content_list:
        content_dic['EWANGELIA KRÓTSZA'].insert(1, content_dic['EWANGELIA DŁUŻSZA'][1])
        content_dic['EWANGELIA KRÓTSZA']

    count = reduce(lambda x, y: x + 1 if 'Refren' in y else x, content_dic['PSALM RESPONSORYJNY'], 0)
    if len(content_dic['PSALM RESPONSORYJNY']) > 6 and count == 1:
        content_dic['PSALM RESPONSORYJNY'].insert(6, 'Refren')
        content_dic['PSALM RESPONSORYJNY'].insert(11, 'Refren')
        # content_dic['PSALM RESPONSORYJNY'].insert(16, 'Refren')
    # content_dic['PSALM RESPONSORYJNY']

    path = r"C:\Users\Acne\Pictures\Cyfrowa Biblia\automatyzacja\paper.gif"
    image_size = 1080
    with Image.open(path) as im:
        out = Image.new("RGB", (image_size, image_size), "white")
        x=0
        y=0
        size_x_left, size_y = im.size

        while x < image_size:
            while y < image_size:
                out.paste(im, (x, y))
                y += size_y
            y = 0
            x += size_x_left

    current_path = f'./web/{thedate}/'
    
    os.makedirs(current_path, exist_ok=True)

    if "DRUGIE CZYTANIE" in content_dic:
        if 'ŚPIEW PRZED EWANGELIĄ' in content_dic["DRUGIE CZYTANIE"]:
            content_dic["DRUGIE CZYTANIE"] = content_dic["DRUGIE CZYTANIE"][:-6]

# def readings_creation():
    min_font_before_pagination = 30
    pagination_font_size = 44

    posts_list = []

    for text in content_dic.keys():
    # .keys():
    # ['PIERWSZE CZYTANIE']:
        if text != 'PSALM RESPONSORYJNY':
            font_size = 43
            returned = draw_text(content_dic, out, text, size_x_left, size_y, font_size)

            if returned['drawn_y'] <= (image_size - 20):
                returned['picture'].save(current_path + f'{text}.png')
                posts_list.append(f'{text}.png')

            while returned['drawn_y'] > image_size - 20:
                if font_size < min_font_before_pagination:
                    pagination_dic = {}
                    if verse_break == 0:
                        verse_break = round((len(content_dic[f'{text}']) - 3) / 2 + 3)
                    pagination_dic[f'{text} cz.1'] = content_dic[f'{text}'][:verse_break]
                    pagination_dic[f'{text} cz.1'].insert(0, f'{text}' )
                    pagination_dic[f'{text} cz.2'] = content_dic[f'{text}'][verse_break:]
                    returned_1 = draw_text_pagination_first(out, pagination_dic[f'{text} cz.1'], size_x_left, size_y, pagination_font_size)
                    returned_2 = draw_text_pagination_second(out, pagination_dic[f'{text} cz.2'], size_x_left, size_y, pagination_font_size)

                    while returned_1['drawn_y'] > image_size - 20 or returned_2['drawn_y'] > image_size - 20:
                        pagination_font_size -= 1
                        returned_1 = draw_text_pagination_first(out, pagination_dic[f'{text} cz.1'], size_x_left, size_y, pagination_font_size)
                        returned_2 = draw_text_pagination_second(out, pagination_dic[f'{text} cz.2'], size_x_left, size_y, pagination_font_size)
                    else:
                        returned_1['picture'].save(current_path + f'{text}1.png')
                        returned_2['picture'].save(current_path + f'{text}2.png')
                        posts_list.append(f'{text}1.png')
                        posts_list.append(f'{text}2.png')
                        
                    break
                else:
                    font_size -= 1
                    returned = draw_text(content_dic, out, text, size_x_left, size_y, font_size)

            else:
                returned['picture'].save(current_path + f'{text}.png')
                posts_list.append(f'{text}.png')

    font_size_psalm = 35
    returned = draw_psalm(content_dic, out, font_size_psalm)
    while returned['drawn_y'] > image_size - 20:
        font_size -= 1
        returned = draw_psalm(content_dic, out, font_size)
    else:
        returned['picture'].save(current_path + 'PSALM RESPONSORYJNY.png')
        posts_list.append('PSALM RESPONSORYJNY.png')
    # print(posts_list)
    
    box = ['/' + str(thedate) + '/', *posts_list]
    return box

@eel.expose
def readings_eng(thedate):
    URL = f"https://www.vaticannews.va/en/word-of-the-day/{str(thedate).replace('-', '/')}.html"
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    content_list = soup.find_all("div", "section__content")[:2]
    content_list_text = [x.get_text().split('\n') for x in content_list]
    for num, y in enumerate(content_list_text):
        content_list_text[num] = [x.replace("\"","") for x in y]
    return content_list_text

@eel.expose
def readings_pol(thedate):
    URL = f"https://liturgia.wiara.pl/kalendarz/67b53.Czytania-mszalne/{str(thedate)}"
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, "html.parser")
    content_list = soup.find_all("div", "txt__rich-area")[1].get_text().split('\n')
    return content_list[3:]
   
if __name__=="__main__":
    draw_post()

