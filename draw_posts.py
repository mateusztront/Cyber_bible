from PIL import ImageDraw, ImageFont
import copy
import textwrap

def draw_text(content_dic, out, name, size_x_left, size_y, font_size):

    tahoma = r"C:\Windows\Fonts\tahoma.ttf"
    tahoma_bold = r"C:\Windows\Fonts\tahomabd.ttf"
    image_size = 1080

    font_size_small = int(0.75 * font_size)

    fnt = ImageFont.truetype(tahoma, font_size) 
    fnt_b = ImageFont.truetype(tahoma_bold, font_size)
    fnt_s = ImageFont.truetype(tahoma, font_size_small)

    size_x_left = int(25/12 * font_size)
    size_x_right = image_size - 2 * size_x_left  
    size_y = int(1.2 * font_size)
    width = int(75 - 0.325 * size_x_left)

    out_func = copy.deepcopy(out)
    draw = ImageDraw.Draw(out_func) 

    draw.text((size_x_left, size_x_left), name, font=fnt_b, fill="red", anchor='lm')
    draw.text((size_x_right + size_x_left, size_x_left), content_dic[name][0], font=fnt_b, fill="red", anchor='rm') #TODO
    
    var_y = size_x_left + size_y
    draw.text((size_x_left, var_y), content_dic[name][1], font=fnt_s, fill="black", anchor='lm')
    
    lines = textwrap.wrap(content_dic[name][2], width=width, initial_indent='     ')
    lines[0] = lines[0].strip()
    for line in lines:
        var_y += size_y
        draw.text((size_x_left, var_y), line, font=fnt_b, fill="black", anchor='lm')
    
    var_y += size_x_left
    
    for count, _ in enumerate(content_dic[name][3:-1]):
        lines = textwrap.wrap(content_dic[name][3+count], width=width, initial_indent='     ')
        lines[0] = lines[0].strip()
        space_length_regular = 15

        for line_count, line in enumerate(lines):
            x_word = size_x_left
            x_word_intended = 2 * size_x_left
            words = line.split(" ")
            words_length = sum(draw.textlength(w, font=fnt) for w in words)
            if len(words) == 1:
                words.append(' ')

            if line_count == len(lines)-1:
                if words_length + (len(words)-1) * space_length_regular > size_x_right:
                    space_length_regular = (size_x_right - words_length) / (len(words) - 1)
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

def draw_text_pagination_first(out, reading_list, size_x_left, size_y, font_size):

    tahoma = r"C:\Windows\Fonts\tahoma.ttf"
    tahoma_bold = r"C:\Windows\Fonts\tahomabd.ttf"
    image_size = 1080

    font_size_small = int(0.75 * font_size)

    fnt = ImageFont.truetype(tahoma, font_size) 
    fnt_b = ImageFont.truetype(tahoma_bold, font_size)
    fnt_s = ImageFont.truetype(tahoma, font_size_small)

    size_x_left = int(25/12 * font_size)
    size_x_right = image_size - 2 * size_x_left
    size_y = int(1.2 * font_size)
    width = int(75 - 0.325 * size_x_left)
    

    out_func = copy.deepcopy(out)
    draw = ImageDraw.Draw(out_func) 

#TODO
    draw.text((size_x_left, size_x_left), reading_list[0], font=fnt_b, fill="red", anchor='lm')
    draw.text((size_x_right + size_x_left, size_x_left), reading_list[1], font=fnt_b, fill="red", anchor='rm') #TODO
    
    var_y = size_x_left + size_y
    draw.text((size_x_left, var_y), reading_list[2], font=fnt_s, fill="black", anchor='lm')
    
    lines = textwrap.wrap(reading_list[3], width=width, initial_indent='     ')
    lines[0] = lines[0].strip()
    for line in lines:
        var_y += size_y
        draw.text((size_x_left, var_y), line, font=fnt_b, fill="black", anchor='lm')
    
    var_y += size_x_left
    
    for count, element in enumerate(reading_list[4:]):
        lines = textwrap.wrap(reading_list[4+count], width=width, initial_indent='     ')
        lines[0] = lines[0].strip()
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
                if words_length + (len(words)-1) * space_length_regular > size_x_right:
                    space_length_regular = (size_x_right - words_length) / (len(words) - 1)
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

def draw_text_pagination_second(out, reading_list, size_x_left, size_y, font_size):

    tahoma = r"C:\Windows\Fonts\tahoma.ttf"
    tahoma_bold = r"C:\Windows\Fonts\tahomabd.ttf"
    image_size = 1080
    font_size_small = int(0.75 * font_size)

    fnt = ImageFont.truetype(tahoma, font_size) 
    fnt_b = ImageFont.truetype(tahoma_bold, font_size)
    fnt_s = ImageFont.truetype(tahoma, font_size_small)

    size_x_left = int(25/12 * font_size)
    size_x_right = image_size - 2 * size_x_left
    size_y = int(1.2 * font_size)
    width = int(75 - 0.325 * size_x_left)

    out_func = copy.deepcopy(out)
    draw = ImageDraw.Draw(out_func) 

    var_y = size_x_left

    lines = textwrap.wrap(reading_list[0], width=width, initial_indent='     ')
    lines[0] = lines[0].strip()
    
    for count, _ in enumerate(reading_list[0:-1]):
        lines = textwrap.wrap(reading_list[0+count], width=width, initial_indent='     ')
        lines[0] = lines[0].strip()
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
                if words_length + (len(words)-1) * space_length_regular > size_x_right:
                    space_length_regular = (size_x_right - words_length) / (len(words) - 1)
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