from operator import itemgetter
import fitz
import json
from pypdf import PdfReader
import io
from PIL import Image
import os
from pdfutils import image_analysis as ia
import re


def remove_invalid_filename_characters(filename):
    cleaned_filename = filename.translate(str.maketrans('','','–— [<>:"-/\\|?*],'))
    return cleaned_filename


def fonts(doc, granularity=False):
    #Extracts fonts and their usage in PDF documents.
    #param doc: PDF document to iterate through
    #type doc: <class 'fitz.fitz.Document'>
    #param granularity: also use 'font', 'flags' and 'color' to discriminate text
    #type granularity: bool
    #rtype: [(font_size, count), (font_size, count}], dict
    #return: most used fonts sorted by count, font style information
  
    styles = {}
    font_counts = {}

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:  # iterate through the text blocks
            if b['type'] == 0:  # block contains text
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        if granularity:
                            identifier = "{0}_{1}_{2}_{3}".format(s['size'], s['flags'], s['font'], s['color'])
                            styles[identifier] = {'size': s['size'], 'flags': s['flags'], 'font': s['font'],
                                                  'color': s['color']}
                        else:
                            identifier = "{0}".format(s['size'])
                            styles[identifier] = {'size': s['size'], 'font': s['font']}

                        font_counts[identifier] = font_counts.get(identifier, 0) + 1  # count the fonts usage

    font_counts = sorted(font_counts.items(), key=itemgetter(1), reverse=True)

    if len(font_counts) < 1:
        raise ValueError("Zero discriminating fonts found!")

    return font_counts, styles

def font_tags(font_counts, styles):
    #Returns dictionary with font sizes as keys and tags as value.

    #param font_counts: (font_size, count) for all fonts occuring in document
    #type font_counts: list
    #param styles: all styles found in the document
    #type styles: dict

    #rtype: dict
    #return: all element tags based on font-sizes

    p_style = styles[font_counts[0][0]]  # get style for most used font by count (paragraph)
    p_size = p_style['size']  # get the paragraph's size

    # sorting the font sizes high to low, so that we can append the right integer to each tag
    font_sizes = []
    for (font_size, count) in font_counts:
        font_sizes.append(float(font_size))
    font_sizes.sort(reverse=True)

    # aggregating the tags for each font size
    idx = 0
    size_tag = {}
    for size in font_sizes:
        idx += 1
        if size == p_size:
            idx = 0
            size_tag[size] = '<p>'
        if size > p_size:
            size_tag[size] = '<h{0}>'.format(idx)
        elif size < p_size:
            size_tag[size] = '<s{0}>'.format(idx)

    return size_tag
def headers_para(doc, size_tag, content_dir, src_file_name):
    #Scrapes headers & paragraphs from PDF and return texts with element tags.
    #when block is image, the image is extracted and saved to content directory

    #param doc: PDF document to iterate through
    #type doc: <class 'fitz.fitz.Document'>
    #param size_tag: textual element tags for each size
    #type size_tag: dict

    #rtype: list of tuples
    #return: tuple of block type, block_size, block_text, image location, block number
    
    header_para = []  # list with headers and paragraphs
   
    first = True  # boolean operator for first header
    previous_s = {}  # previous span
    page_num = 0
    block_num = 0
    for page in doc:
        image_num = 0
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:  # iterate through the text blocks
            block_num += 1
            if b['type'] == 0:  # this block contains text
                # REMEMBER: multiple fonts and sizes are possible IN one block
                block_text = ""  # text found in block
                block_size = "" # size of text found in block (header, paragraph, etc)
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        if s['text'].strip():  # removing whitespaces:
                            if first:
                                previous_s = s
                                first = False
                                block_text =  s['text']
                                block_size = size_tag[s['size']] 
                            else:
                                if s['size'] == previous_s['size']:
                                    if block_text == "":
                                        # new block has started, so append size tag
                                        block_text =  s['text']
                                        block_size = size_tag[s['size']]
                                    else:  # in the same block, so concatenate strings
                                        block_text += " " + s['text']

                                else:
                                    
                                    # block type, block_size, block_text, image location, block number
                                    block_elements = ("text", block_size, block_text, "", block_num, b,page_num)
                                    header_para.append(block_elements)
                                    block_text =  s['text']
                                    block_size = size_tag[s['size']]
                                    block_num += 1
                                   
                                previous_s = s

                    # new block started
                    block_text += ""
                block_elements = ("text", block_size, block_text, "", block_num, b,page_num)
                header_para.append(block_elements)
                
            elif b['type'] ==1: #this block is an image
                img_bytes =b['image']
                img_ext = b['ext']
                image_num += 1
                image = Image.open(io.BytesIO(img_bytes))
                if not (image.height <=50 or image.width<= 50): #ignore images too small for analysis
                    if ia.analyze_image_text(img_bytes): #returns true if image contains text, disregard textless images
                        src_file_name = os.path.splitext(os.path.basename(src_file_name))[0]
                        dest_file_name= f"{src_file_name}{page_num}_{image_num}.{img_ext}"
                        img_file = os.path.join(content_dir, dest_file_name )
                        image.save(open(img_file, "wb"))
                        block_elements = ("image", "", "", img_file, block_num, b, page_num)
                        header_para.append(block_elements)
        page_num += 1
    return header_para
import sys
def article_extraction(doc_elements, doc_title):
    extracted_elements = []
    found_title_element = False
    for doc_element in  doc_elements:
        if doc_element[1] == '<h1>' and doc_title in remove_invalid_filename_characters(doc_element[2]): #indicates we have found the start of article
            found_title_element = True
            #extracted_elements.append(doc_element)
        elif doc_element[1] == '<h1>' and doc_title not in doc_element[2]:
            found_title_element = False
        if found_title_element: 
            extracted_elements.append(doc_element)
    return extracted_elements

    
            
def format_elements(doc_elements, html = False):
    returned_text = ""
    first_in_bullet_list = True
    first_in_number_list = True
    if html:
        returned_text = """ <!DOCTYPE html> 
                            <html lang='en'>
                            <head>
                            <meta charset='UTF-8'>
                            <meta http-equiv='X-UA-Compatible' content='IE=edge'>
                            <meta name='viewport' content='width=device-width, initial-scale=1.0'>
                            <link rel='stylesheet' href='style.css'>
                            <script src='main.js'></script>
                            <title>Document</title>
                           </head>
                            <body>"""
        
    for doc_element in  doc_elements:
        if html:
                element_text = doc_element[2].lstrip()
                if doc_element[0] == 'text':
                    if  doc_element[1] == '<h1>':
                        returned_text += f"<div><h1><span> {element_text} </span></h1></div>"
                    elif  doc_element[1] == '<h2>':
                        returned_text += f"<div><h2><span>{element_text} </span></h2></div>"
                    elif  doc_element[1] == '<h3>':
                        returned_text += f"<div><h3><span>{element_text}</span></h3></div>"
                    elif 's' in doc_element[1] :
                        returned_text += f"<span class='small' {element_text} </span>"
                    else:
                        if element_text != "":
                            if element_text.startswith("\N{BULLET}") or element_text[0].isdigit():
                                if element_text.startswith("\N{BULLET}"):
                                    if first_in_bullet_list:
                                        returned_text +=  f"<ul><li>{element_text}</li>"
                                        first_in_bullet_list = False
                                    else:
                                        returned_text +=  f"<li>{element_text}</li>"
                                else:
                                    if first_in_bullet_list==False:
                                        returned_text +=  f"</ul>{element_text}"
                                        first_in_bullet_list = True
                                    else:
                                        if element_text[0].isdigit():
                                            element_text = element_text[2:] #removing digit and what immediate follows so numbers are not repeated
                                            if first_in_number_list:
                                                returned_text +=  f"<ol><li>{element_text}</li>"
                                                first_in_number_list = False
                                            else:
                                                returned_text +=  f"<li>{element_text}</li>"
                                        else:
                                            if first_in_number_list==False:
                                                returned_text +=  f"</ol>{element_text}"
                                                first_in_number_list = True
                            else:  
                                returned_text +=  element_text
                elif doc_element[0] == 'image':
                      returned_text += f"<br><img src='{os.path.basename(doc_element[3])}'><br>"
        else:
            returned_text += doc_element[2] + "\n" 
    if html:       
        returned_text += "</body></html>"
        return returned_text 
    else: 
        return returned_text

def save_to_content(doc_text, doc_file_name, dir_location):
    doc_title = os.path.splitext(os.path.basename(doc_file_name))[0]
    target_name = doc_title +".html"
    target_path = os.path.join(dir_location, target_name )
    f = open(target_path, "w", encoding='utf-8')
    f.write(doc_text)
    f.close()
    return target_path

def image_extraction(doc, content_dir, src_file_name):
    image_extracts = []  # list with filenames
    page_num = 0
    for page in doc:
        page_num += 1
        image_num = 0
        blocks = page.get_text("dict")["blocks"]
        
        for b in blocks:  # iterate through the text blocks
            if b['type'] ==1: #this block is an image
                img_bytes =b['image']
                img_ext = b['ext']
                image_num += 1
                image = Image.open(io.BytesIO(img_bytes))
                src_file_name = os.path.splitext(os.path.basename(src_file_name))[0]
                dest_file_name= f"{src_file_name}{page_num}_{image_num}.{img_ext}"
                img_file = os.path.join(content_dir, dest_file_name )
                image.save(open(img_file, "wb"))
                block_elements = ("image", img_file)
                image_extracts.append(block_elements)
    return image_extracts

def table_extraction(doc, content_dir, src_file_name):
    table_extracts = []  # list with filenames
    page_num = 0
    for page in doc:
        page_num += 1
        table_num = 0
        tabs = page.find_tables()
        for tab in tabs:
            table_num += 1 #going to treat tables as separate blocks for our analysis
            src_file_name = os.path.splitext(os.path.basename(src_file_name))[0]
            dest_file_name= f"{src_file_name}{page_num}_{table_num}.html"
            tab_file = os.path.join(content_dir, dest_file_name )
            try:
                with  open(tab_file, 'w') as file:
                    df = tab.to_pandas()
                    file.write(df.to_html())
                    block_elements = ("table", tab_file)
                    table_extracts.append(block_elements)
            except:
                print("Error Creating Table")
    return table_extracts

def text_extraction(source_file):
    found_text=""
    reader = PdfReader(source_file)
    for page in  reader.pages:
       found_text= found_text + "\n" + page.extract_text()
    return found_text

def extract_2_pdf(source_file, article_extract_elements, content_dir, dir_file):
    
    doc2 = fitz.open(source_file) # open document
   
    crop_rect_start_page = article_extract_elements[0][6]
    crop_rect_end_page = article_extract_elements[-1][6]
   
    for page in doc2:
        start_page = True
        for element in article_extract_elements:
           
            if not(page.number < crop_rect_start_page):
                if page.number == crop_rect_start_page:
                    if start_page:
                        page_crop_rect_X0 = 0
                        page_crop_rect_Y0 = element[5]['bbox'][1]
                        page_crop_rect_X1 = page.rect.width 
                        page_crop_rect_Y1 = page.rect.height 
                        start_page = False
                elif (page.number > crop_rect_start_page) and (page.number < crop_rect_end_page):
                    page_crop_rect_X0 = 0
                    page_crop_rect_Y0 = 0
                    page_crop_rect_X1 = page.rect.width
                    page_crop_rect_Y1 = page.rect.height
                        
                elif (page.number > crop_rect_start_page) and (page.number == crop_rect_end_page):
                    page_crop_rect_X0 = 0
                    page_crop_rect_Y0 = 0
                    page_crop_rect_X1 = page.rect.width
                    page_crop_rect_Y1 =element[5]['bbox'][1]
           
        try:
            page.set_cropbox(fitz.Rect(page_crop_rect_X0, page_crop_rect_Y0, page_crop_rect_X1, page_crop_rect_Y1))
        except:
            print("page could not be cropped")
    target = os.path.join(content_dir, dir_file)
    doc2.save(target)
    return target
    

def convert_pdf_2_html(src_file_name, dir_location):
    doc = fitz.open(src_file_name)  # open document
    doc_title = os.path.splitext(os.path.basename(src_file_name))[0]
    target_name = doc_title +".html"
    target_path = os.path.join(dir_location, target_name )
    out = open(target_path, "wb")  # open text output
    for page in doc:  # iterate the document pages
        page.read_contents()
        text = page.get_text('html', clip = None).encode("utf8")  
        out.write(text)  # write text of page
        #out.write(bytes((12,)))  # write page delimiter (form feed 0x0C)
    out.close()
    return target_path

    
    
