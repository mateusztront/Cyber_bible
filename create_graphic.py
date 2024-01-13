import eel
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import copy
import textwrap
from pathlib import WindowsPath
from datetime import date
import os

@eel.expose
def draw_text():

    today = date.today()

    URL = f"https://liturgia.wiara.pl/kalendarz/67b53.Czytania-mszalne/{str(today)}"


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
                if '' == text:
                    continue
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


    # content_dic['PSALM RESPONSORYJNY'].insert(6, 'Refren')
    # content_dic['PSALM RESPONSORYJNY'].insert(11, 'Refren')
    # content_dic['PSALM RESPONSORYJNY'].insert(16, 'Refren')
    content_dic['PSALM RESPONSORYJNY']

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


    tahoma = r"C:\Windows\Fonts\tahoma.ttf"
    tahoma_bold = r"C:\Windows\Fonts\tahomabd.ttf"

    # current_path = WindowsPath(r'C:\Users\Acne\Pictures\Cyfrowa Biblia\\' + str(today))
    current_path = f'./web/{today}/'
    
    os.makedirs(current_path, exist_ok=True)

    def draw_text(out, name, current_path, size_x_left, size_y, font_size):

        font_size_small = int(0.75 * font_size)

        fnt = ImageFont.truetype(tahoma, font_size) 
        fnt_b = ImageFont.truetype(tahoma_bold, font_size)
        fnt_s = ImageFont.truetype(tahoma, font_size_small)

        size_x_left = int(25/12 * font_size)
        size_x_right = image_size - 2 * size_x_left  
        size_y = int(1.2 * font_size)
        width = int(80 - 0.325 * size_x_left)

        out_func = copy.deepcopy(out)
        draw = ImageDraw.Draw(out_func) 

        draw.text((size_x_left, size_x_left), name, font=fnt_b, fill="red", anchor='lm')
        draw.text((size_x_right + size_x_left, size_x_left), content_dic[name][0], font=fnt_b, fill="red", anchor='rm') #TODO
        
        var_y = size_x_left + size_y
        draw.text((size_x_left, var_y), content_dic[name][1], font=fnt_s, fill="black", anchor='lm')
        
        lines = textwrap.wrap(content_dic[name][2], width=width)
        for line in lines:
            var_y += size_y
            draw.text((size_x_left, var_y), line, font=fnt_b, fill="black", anchor='lm')
        
        var_y += size_x_left
        
        for count, element in enumerate(content_dic[name][3:-1]):
            lines = textwrap.wrap(content_dic[name][3+count], width=width)
            space_length_regular = 15

            for line_count, line in enumerate(lines):
                x_word = size_x_left
                x_word_intended = 2 * size_x_left
                words = line.split(" ")
                words_length = sum(draw.textlength(w, font=fnt) for w in words)
                if len(words)==1:
                    words.append(' ')

                if line_count == len(lines)-1:
                    for word in words:
                        draw.text((x_word, var_y), word, font=fnt, fill="black", anchor='lm')
                        x_word += draw.textlength(word, font=fnt) + space_length_regular
                    var_y += size_y  
                    break
                
                space_length_intended = (size_x_right - x_word - words_length) / (len(words) - 1)
                space_length_regular = (size_x_right - words_length) / (len(words) - 1)
            
                if line_count == 0 and line != 'Bracia:' and 'Jezus powiedział' not in line:
                    for word in words:
                        draw.text((x_word_intended, var_y), word, font=fnt, fill="black", anchor='lm')
                        x_word_intended += draw.textlength(word, font=fnt) + space_length_intended

                else:
                    for word in words:
                        draw.text((x_word, var_y), word, font=fnt, fill="black", anchor='lm')
                        x_word += draw.textlength(word, font=fnt) + space_length_regular
                var_y += size_y            
                
        draw.text((2*size_x_left, var_y+size_y), content_dic[name][-1], font=fnt_b, fill="black", anchor='lm')

        returned = {'drawn_y': var_y+size_y, 'picture': out_func}

        return returned

        out_func = copy.deepcopy(out)


    if "DRUGIE CZYTANIE" in content_dic:
        if 'ŚPIEW PRZED EWANGELIĄ' in content_dic["DRUGIE CZYTANIE"]:
            content_dic["DRUGIE CZYTANIE"] = content_dic["DRUGIE CZYTANIE"][:-6]


    def draw_text_pagination_first(out, reading_list, current_path, size_x_left, size_y, font_size):

        font_size_small = int(0.75 * font_size)

        fnt = ImageFont.truetype(tahoma, font_size) 
        fnt_b = ImageFont.truetype(tahoma_bold, font_size)
        fnt_s = ImageFont.truetype(tahoma, font_size_small)

        size_x_left = int(25/12 * font_size)
        size_x_right = image_size - 2 * size_x_left
        size_y = int(1.2 * font_size)
        width = int(80 - 0.35 * size_x_left)

        out_func = copy.deepcopy(out)
        draw = ImageDraw.Draw(out_func) 

    #TODO
        draw.text((size_x_left, size_x_left), reading_list[0], font=fnt_b, fill="red", anchor='lm')
        draw.text((size_x_right + size_x_left, size_x_left), reading_list[1], font=fnt_b, fill="red", anchor='rm') #TODO
        
        var_y = size_x_left + size_y
        draw.text((size_x_left, var_y), reading_list[2], font=fnt_s, fill="black", anchor='lm')
        
        lines = textwrap.wrap(reading_list[3], width=width)
        for line in lines:
            var_y += size_y
            draw.text((size_x_left, var_y), line, font=fnt_b, fill="black", anchor='lm')
        
        var_y += size_x_left
        
        for count, element in enumerate(reading_list[4:]):
            lines = textwrap.wrap(reading_list[4+count], width=width)
            space_length_regular = 15

            for line_count, line in enumerate(lines):
                x_word = size_x_left
                x_word_intended = 2 * size_x_left
                words = line.split(" ")
                words_length = sum(draw.textlength(w, font=fnt) for w in words)
                if len(words)==1:
                    words.append(' ')

                    for word in words:
                        draw.text((x_word, var_y), word, font=fnt, fill="black", anchor='lm')
                        x_word += draw.textlength(word, font=fnt) + space_length_regular
                    var_y += size_y  
                    break

                if line_count == len(lines)-1:
                    for word in words:
                        draw.text((x_word, var_y), word, font=fnt, fill="black", anchor='lm')
                        x_word += draw.textlength(word, font=fnt) + space_length_regular
                    var_y += size_y  
                    break
                
                space_length_intended = (size_x_right - x_word - words_length) / (len(words) - 1)
                space_length_regular = (size_x_right - words_length) / (len(words) - 1)
            
                if line_count == 0 and line != 'Bracia:' and 'Jezus powiedział' not in line:
                    for word in words:
                        draw.text((x_word_intended, var_y), word, font=fnt, fill="black", anchor='lm')
                        x_word_intended += draw.textlength(word, font=fnt) + space_length_intended

                else:
                    for word in words:
                        draw.text((x_word, var_y), word, font=fnt, fill="black", anchor='lm')
                        x_word += draw.textlength(word, font=fnt) + space_length_regular
                var_y += size_y            
                

        returned = {'drawn_y': var_y+size_y, 'picture': out_func}

        return returned

    def draw_text_pagination_second(out, reading_list, current_path, size_x_left, size_y, font_size):

        font_size_small = int(0.75 * font_size)
    
        fnt = ImageFont.truetype(tahoma, font_size) 
        fnt_b = ImageFont.truetype(tahoma_bold, font_size)
        fnt_s = ImageFont.truetype(tahoma, font_size_small)

        size_x_left = int(25/12 * font_size)
        size_x_right = image_size - 2 * size_x_left
        size_y = int(1.2 * font_size)
        width = int(80 - 0.35 * size_x_left)

        out_func = copy.deepcopy(out)
        draw = ImageDraw.Draw(out_func) 

        var_y = size_x_left
        
        lines = textwrap.wrap(reading_list[0], width=width)
        
        for count, element in enumerate(reading_list[0:-1]):
            lines = textwrap.wrap(reading_list[0+count], width=width)
            space_length_regular = 15

            for line_count, line in enumerate(lines):
                x_word = size_x_left
                x_word_intended = 2 * size_x_left
                words = line.split(" ")
                words_length = sum(draw.textlength(w, font=fnt) for w in words)
                if len(words)==1:
                    words.append(' ')

                    for word in words:
                        draw.text((x_word, var_y), word, font=fnt, fill="black", anchor='lm')
                        x_word += draw.textlength(word, font=fnt) + space_length_regular
                    var_y += size_y  
                    break

                if line_count == len(lines)-1:
                    for word in words:
                        draw.text((x_word, var_y), word, font=fnt, fill="black", anchor='lm')
                        x_word += draw.textlength(word, font=fnt) + space_length_regular
                    var_y += size_y  
                    break
                
                space_length_intended = (size_x_right - x_word - words_length) / (len(words) - 1)
                space_length_regular = (size_x_right - words_length) / (len(words) - 1)
            
                if line_count == 0 and line != 'Bracia:' and 'Jezus powiedział' not in line:
                    for word in words:
                        draw.text((x_word_intended, var_y), word, font=fnt, fill="black", anchor='lm')
                        x_word_intended += draw.textlength(word, font=fnt) + space_length_intended

                else:
                    for word in words:
                        draw.text((x_word, var_y), word, font=fnt, fill="black", anchor='lm')
                        x_word += draw.textlength(word, font=fnt) + space_length_regular
                var_y += size_y            
                
        draw.text((2*size_x_left, var_y+size_y), reading_list[-1], font=fnt_b, fill="black", anchor='lm')
        returned = {'drawn_y': var_y+size_y, 'picture': out_func}

        return returned

# def readings_creation():
    font_size = 36
    min_font_before_pagination = 29
    verse_break = 6
    pagination_font_size = 28

    posts_list = []
    for text in content_dic.keys():
    # ['PIERWSZE CZYTANIE']:
        if text != 'PSALM RESPONSORYJNY':
   
            returned = draw_text(out, text, current_path, size_x_left, size_y, font_size)

            while returned['drawn_y'] > image_size - 20:
                if font_size < min_font_before_pagination:
                    pagination_dic = {}
                    pagination_dic[f'{text} cz.1'] = content_dic[f'{text}'][:verse_break]
                    pagination_dic[f'{text} cz.1'].insert(0, f'{text}' )
                    pagination_dic[f'{text} cz.2'] = content_dic[f'{text}'][verse_break:]
                    
                    returned = draw_text_pagination_first(out, pagination_dic[f'{text} cz.1'], current_path, size_x_left, size_y, pagination_font_size)
                    returned['picture'].show()
                    returned['picture'].save(current_path + f'{text}1.png')

                    returned = draw_text_pagination_second(out,  pagination_dic[f'{text} cz.2'], current_path, size_x_left, size_y, pagination_font_size)
                    returned['picture'].show()
                    returned['picture'].save(current_path + f'{text}2.png')

                    

                    break
                
                else:
                    font_size -= 1
                    returned = draw_text(out, text, current_path, size_x_left, size_y, font_size)
            
            # print('font_size: ', font_size)
            returned['picture'].show()
            returned['picture'].save(current_path + f'{text}.png')
            

    font_size_psalm = 30
    font_size_small_psalm = int(0.75 * font_size_psalm)

    tahoma = r"C:\Windows\Fonts\tahoma.ttf"
    tahoma_bold = r"C:\Windows\Fonts\tahomabd.ttf"

    fnt_psalm = ImageFont.truetype(tahoma, font_size_psalm) 
    fnt_b_psalm = ImageFont.truetype(tahoma_bold, font_size_psalm)
    fnt_s_psalm = ImageFont.truetype(tahoma, font_size_small_psalm)


    # content_dic["PSALM RESPONSORYJNY"].insert(16, 'Refren')
    content_dic["PSALM RESPONSORYJNY"]

    if len(content_dic["PSALM RESPONSORYJNY"][0]) > 35:
        content_dic["PSALM RESPONSORYJNY"][0] = content_dic["PSALM RESPONSORYJNY"][0].split(',')[0]
        
    # del content_dic["PSALM RESPONSORYJNY"][-2]
    # content_dic["PSALM RESPONSORYJNY"].insert(-1, 'pójdźcie, narody, oddajcie pokłon Panu,')
    # content_dic["PSALM RESPONSORYJNY"].insert(-1, 'bo wielka światłość zstąpiła dzisiaj na ziemię.')
    content_dic["PSALM RESPONSORYJNY"]


    out_psalm = copy.deepcopy(out)
    draw = ImageDraw.Draw(out_psalm) 

    y_distance = font_size_psalm * 0.95
    y_further_distance = font_size_psalm * 1.1
    x_distance = font_size_psalm * 2

    draw.text((x_distance, y_further_distance*2), "PSALM RESPONSORYJNY", font=fnt_b_psalm, fill="red", anchor='lm')
    draw.text((1000, y_further_distance*2), content_dic["PSALM RESPONSORYJNY"][0], font=fnt_b_psalm, fill="red", anchor='rm')
    draw.text((x_distance, y_further_distance*3), "Refren: ", font=fnt_b_psalm, fill="red", anchor='lm')
    draw.text((x_distance*3, y_further_distance*3), content_dic["PSALM RESPONSORYJNY"][1][7:], font=fnt_b_psalm, fill="black", anchor='lm')

    y_text = y_further_distance*4
    for count, element in enumerate(content_dic["PSALM RESPONSORYJNY"][2:]):

        if "Refren" in element :
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
            draw.text((x_distance, y_text+y_further_distance), "Aklamacja: ", font=fnt_b_psalm, fill="red", anchor='lm')
            draw.text((x_distance*4, y_text+y_further_distance), acclamation[2][10:], font=fnt_b_psalm, fill="black", anchor='lm')
            draw.text((x_distance*2, y_text+y_further_distance*2), acclamation[3], font=fnt_psalm, fill="black", anchor='lm')
            draw.text((x_distance*2, y_text+y_further_distance*2+y_distance), acclamation[4], font=fnt_psalm, fill="black", anchor='lm')
            # draw.text((x_distance*2, y_text+y_further_distance*3+y_distance), acclamation[5], font=fnt_psalm, fill="black", anchor='lm')

            draw.text((x_distance, y_text+y_further_distance*3+y_distance), "Aklamacja: ", font=fnt_b_psalm, fill="red", anchor='lm') 
            draw.text((x_distance*4, y_text+y_further_distance*3+y_distance), acclamation[5][10:], font=fnt_b_psalm, fill="black", anchor='lm')

            break  

    # TODO
        elif 'albo' in element:
            continue

        else:
            draw.text((x_distance*2, y_text), element, font=fnt_psalm, fill="black", anchor='lm')
        y_text += y_distance

    out_psalm.show()
    out_psalm.save(current_path + 'PSALM RESPONSORYJNY.png')
    
    
    box = ['/' + str(today) + '/', *content_dic.keys()]
    return box
   
if __name__=="__main__":
    draw_text()

