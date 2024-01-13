from datetime import date
import random
import eel 
from random import randint 
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import copy
import textwrap
from pathlib import Path, PureWindowsPath, WindowsPath
from datetime import date
import os

from create_graphic import draw_text 
# from create_graphic import draw_text  
eel.init("web")   
  
# Exposing the random_python function to javascript 
@eel.expose     
def random_python(): 
    print("Random function running") 
    return randint(1,100) 


# def draw_text():
    
#     name = 'EWANGELIA'

#     today = date.today()


#     URL = f"https://liturgia.wiara.pl/kalendarz/67b53.Czytania-mszalne/{str(today)}"
#     # URL = f"https://liturgia.wiara.pl/kalendarz/67b53.Czytania-mszalne/2023-11-23"

#     page = requests.get(URL)

#     soup = BeautifulSoup(page.content, "html.parser")

#     content_list = soup.find_all("div", "txt__rich-area")[1].get_text().split('\n')

#     if content_list[-1] == '':
#         del content_list[-1]





#     content_list


#     # content_list[content_list.index('EWANGELIA')]


#     if 'EWANGELIA DŁUŻSZA' in content_list:
#         cut_points = ['PIERWSZE CZYTANIE', 'PSALM RESPONSORYJNY', 'DRUGIE CZYTANIE', 'EWANGELIA DŁUŻSZA', 'EWANGELIA KRÓTSZA']
#     elif 'DRUGIE CZYTANIE' in content_list:
#         cut_points = ['PIERWSZE CZYTANIE', 'PSALM RESPONSORYJNY', 'DRUGIE CZYTANIE', 'EWANGELIA']
#     else:
#         cut_points = ['PIERWSZE CZYTANIE', 'PSALM RESPONSORYJNY', 'EWANGELIA']

#     content_dic = {}
#     staging_list = [] 


#     for text in content_list:
#         if 'Liturgia Słowa' in text or '' == text:
#             continue
        

#         # content_list[content_list.index(text)] = text.strip()
#         # text = text.strip()
        
#         if text in cut_points:

#             for text in content_list[content_list.index(text)+1:]:
#                 if '' == text:
#                     continue
#                 if text not in cut_points:
#                     staging_list.append(text)
                    
#                 else:
#                     content_dic[cut_points[0]] = staging_list
#                     staging_list = [] 
#                     del cut_points[0]
#                     break
            
#             content_dic[cut_points[0]] = staging_list

#     # content_dic 

            


#     content_dic.keys()


#     if 'EWANGELIA KRÓTSZA' in content_list:
#         content_dic['EWANGELIA KRÓTSZA'].insert(1, content_dic['EWANGELIA DŁUŻSZA'][1])
#         content_dic['EWANGELIA KRÓTSZA']


#     path = r"C:\Users\Acne\Pictures\Cyfrowa Biblia\automatyzacja\paper.gif"

#     image_size = 1080
#     with Image.open(path) as im:
#         out = Image.new("RGB", (image_size, image_size), "white")
#         x=0
#         y=0
#         size_x_left, size_y = im.size

#         while x < image_size:
#             while y < image_size:
#                 out.paste(im, (x, y))
#                 y += size_y
#             y = 0
#             x += size_x_left

#     # out.show()



#     tahoma = r"C:\Windows\Fonts\tahoma.ttf"
#     tahoma_bold = r"C:\Windows\Fonts\tahomabd.ttf"


#     # current_path = WindowsPath(r'C:\Users\Acne\Pictures\Cyfrowa Biblia\\' + str(today))
#     current_path = WindowsPath(r'C:/Users/Acne/Pictures/Cyfrowa Biblia/automatyzacja/Cyber_bible/web/' + str(today))

#     os.makedirs(current_path, exist_ok=True)

#     font_size = 34
#     font_size_small = int(0.75 * font_size)

#     fnt = ImageFont.truetype(tahoma, font_size) 
#     fnt_b = ImageFont.truetype(tahoma_bold, font_size)
#     fnt_s = ImageFont.truetype(tahoma, font_size_small)

#     size_x_left = int(25/12 * font_size)
#     size_x_right = image_size - 2 * size_x_left  
#     size_y = int(1.2 * font_size)
#     width = int(80 - 0.35 * size_x_left)

#     out_func = copy.deepcopy(out)
#     draw = ImageDraw.Draw(out_func) 

#     draw.text((size_x_left, size_x_left), name, font=fnt_b, fill="red", anchor='lm')
#     draw.text((size_x_right + size_x_left, size_x_left), content_dic[name][0], font=fnt_b, fill="red", anchor='rm') #TODO
    
#     var_y = size_x_left + size_y
#     draw.text((size_x_left, var_y), content_dic[name][1], font=fnt_s, fill="black", anchor='lm')
    
#     lines = textwrap.wrap(content_dic[name][2], width=width)
#     for line in lines:
#         var_y += size_y
#         draw.text((size_x_left, var_y), line, font=fnt_b, fill="black", anchor='lm')
    
#     var_y += size_x_left
    
#     for count, element in enumerate(content_dic[name][3:-1]):
#         lines = textwrap.wrap(content_dic[name][3+count], width=width)
#         space_length_regular = 15

#         for line_count, line in enumerate(lines):
#             x_word = size_x_left
#             x_word_intended = 2 * size_x_left
#             words = line.split(" ")
#             words_length = sum(draw.textlength(w, font=fnt) for w in words)
#             if len(words)==1:
#                 words.append(' ')

#             if line_count == len(lines)-1:
#                 for word in words:
#                     draw.text((x_word, var_y), word, font=fnt, fill="black", anchor='lm')
#                     x_word += draw.textlength(word, font=fnt) + space_length_regular
#                 var_y += size_y  
#                 break
            
#             space_length_intended = (size_x_right - x_word - words_length) / (len(words) - 1)
#             space_length_regular = (size_x_right - words_length) / (len(words) - 1)
           
#             if line_count == 0 and line != 'Bracia:' and 'Jezus powiedział' not in line:
#                 for word in words:
#                     draw.text((x_word_intended, var_y), word, font=fnt, fill="black", anchor='lm')
#                     x_word_intended += draw.textlength(word, font=fnt) + space_length_intended

#             else:
#                 for word in words:
#                     draw.text((x_word, var_y), word, font=fnt, fill="black", anchor='lm')
#                     x_word += draw.textlength(word, font=fnt) + space_length_regular
#             var_y += size_y            
            
#     draw.text((2*size_x_left, var_y+size_y), content_dic[name][-1], font=fnt_b, fill="black", anchor='lm')

#     # out_func.show()

#     returned = {'drawn_y': var_y+size_y, 'picture': out_func}

#     out_func.save(current_path / f'{name}.png')

#     path = current_path / f'{name}.png'
#     box = str(today) + '\\'
#     return box

@eel.expose
def py_random():
    return random.random()


# Start the index.html file 
eel.start("index.html", size=(800, 800))
