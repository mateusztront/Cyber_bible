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

from create_graphic import draw_text, readings_eng, readings_pol
# from create_graphic import draw_text  
eel.init("web")   

# @eel.expose
# def py_random():
#     return random.random()


# Start the index.html file 
eel.start("index.html", size=(800, 800))
