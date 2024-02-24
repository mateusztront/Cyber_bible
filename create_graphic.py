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
    pagination_font_size = 36

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
                    pagination_dic[f'{text} cz.1'] = content_dic[f'{text}'][:verse_break]
                    pagination_dic[f'{text} cz.1'].insert(0, f'{text}' )
                    pagination_dic[f'{text} cz.2'] = content_dic[f'{text}'][verse_break:]
                    
                    returned = draw_text_pagination_first(out, pagination_dic[f'{text} cz.1'], size_x_left, size_y, pagination_font_size)
                    returned['picture'].save(current_path + f'{text}1.png')
                    posts_list.append(f'{text}1.png')

                    returned = draw_text_pagination_second(out,  pagination_dic[f'{text} cz.2'], size_x_left, size_y, pagination_font_size)
                    returned['picture'].save(current_path + f'{text}2.png')
                    posts_list.append(f'{text}2.png')

                    break
                else:
                    font_size -= 1
                    returned = draw_text(content_dic, out, text, size_x_left, size_y, font_size)

            else:
                returned['picture'].save(current_path + f'{text}.png')
                posts_list.append(f'{text}.png')
            
    font_size_psalm = 30
    font_size_small_psalm = int(0.75 * font_size_psalm)

    tahoma = r"C:\Windows\Fonts\tahoma.ttf"
    tahoma_bold = r"C:\Windows\Fonts\tahomabd.ttf"

    fnt_psalm = ImageFont.truetype(tahoma, font_size_psalm) 
    fnt_b_psalm = ImageFont.truetype(tahoma_bold, font_size_psalm)
    fnt_s_psalm = ImageFont.truetype(tahoma, font_size_small_psalm)


    # content_dic["PSALM RESPONSORYJNY"].insert(16, 'Refren')
    content_dic["PSALM RESPONSORYJNY"]

    if len(content_dic["PSALM RESPONSORYJNY"][0]) > 30:
        content_dic["PSALM RESPONSORYJNY"][0] = content_dic["PSALM RESPONSORYJNY"][0].split(',')[0]
        
    # del content_dic["PSALM RESPONSORYJNY"][-2]
    # content_dic["PSALM RESPONSORYJNY"].insert(-1, 'pójdźcie, narody, oddajcie pokłon Panu,')
    # content_dic["PSALM RESPONSORYJNY"].insert(-1, 'bo wielka światłość zstąpiła dzisiaj na ziemię.')
    content_dic["PSALM RESPONSORYJNY"]

    out_psalm = copy.deepcopy(out)
    draw = ImageDraw.Draw(out_psalm) 

    y_distance = font_size_psalm * 0.95
    y_further_distance = font_size_psalm * 0.7
    x_distance = font_size_psalm * 2

    draw.text((x_distance, y_further_distance*2), "PSALM RESPONSORYJNY", font=fnt_b_psalm, fill="red", anchor='lm')
    draw.text((1000, y_further_distance*2), content_dic["PSALM RESPONSORYJNY"][0], font=fnt_b_psalm, fill="red", anchor='rm')
    draw.text((x_distance, y_further_distance*4), "Refren: ", font=fnt_b_psalm, fill="red", anchor='lm')
    draw.text((x_distance*3, y_further_distance*4), content_dic["PSALM RESPONSORYJNY"][1][7:], font=fnt_b_psalm, fill="black", anchor='lm')

    y_text = y_further_distance*6
    for count, element in enumerate(content_dic["PSALM RESPONSORYJNY"][2:]):

        if "Refren" in element:
            y_text += y_further_distance
            draw.text((x_distance, y_text), "Refren: ", font=fnt_b_psalm, fill="red", anchor='lm')
            draw.text((x_distance*3, y_text), content_dic["PSALM RESPONSORYJNY"][1][7:], font=fnt_b_psalm, fill="black", anchor='lm')
            y_text += y_further_distance
        elif "ŚPIEW PRZED EWANGELIĄ" in element:
            acclamation = content_dic["PSALM RESPONSORYJNY"][count+2:]
            # if 'ŚPIEW' in acclamation[0]:
            #     acclamation.insert(1, '')
            # print(acclamation)
            draw.text((x_distance, y_text), "AKLAMACJA PRZED EWANGELIĄ", font=fnt_b_psalm, fill="red", anchor='lm')
            draw.text((1000, y_text), acclamation[1], font=fnt_b_psalm, fill="red", anchor='rm')
            draw.text((x_distance, y_text+y_further_distance*2), "Aklamacja: ", font=fnt_b_psalm, fill="red", anchor='lm')
            draw.text((x_distance*4, y_text+y_further_distance*2), acclamation[2][10:], font=fnt_b_psalm, fill="black", anchor='lm')
            draw.text((x_distance*2, y_text+y_further_distance*4), acclamation[3], font=fnt_psalm, fill="black", anchor='lm')
            draw.text((x_distance*2, y_text+y_further_distance*4+y_distance), acclamation[4], font=fnt_psalm, fill="black", anchor='lm')
            # draw.text((x_distance*2, y_text+y_further_distance*3+y_distance), acclamation[5], font=fnt_psalm, fill="black", anchor='lm')

            draw.text((x_distance, y_text+y_further_distance*6+y_distance), "Aklamacja: ", font=fnt_b_psalm, fill="red", anchor='lm') 
            draw.text((x_distance*4, y_text+y_further_distance*6+y_distance), acclamation[5][10:], font=fnt_b_psalm, fill="black", anchor='lm')
            break  
    # TODO
        elif 'albo' in element:
            continue

        else:
            draw.text((x_distance*2, y_text), element, font=fnt_psalm, fill="black", anchor='lm')
        y_text += y_distance

    # out_psalm.show()
    out_psalm.save(current_path + 'PSALM RESPONSORYJNY.png')
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

