#!/usr/bin/python
import sys
import os
import io
import re
import bs4
import numpy
import string
import requests
import unicodedata
from PIL import Image
from bs4 import BeautifulSoup
from os import path

class book_part:
    def __init__(self, name):
        self.name = name
        self.chapters = []

class multi_row:
    def __init__(self, height, loc_x, loc_y):
        self.height = height
        self.loc_x = loc_x
        self.loc_y = loc_y

class imabi_converter:
    '''
    Class for converting imabi.net to latex format
    '''
    def __init__(self):
        self.offline = True
        self.table_cntr = 0
        self.table_row_cntr = 0
        self.table_cell_cntr = 0
        self.table_mrows = []
        self.table_width = 0

        self.inside_list = False
        self.inside_table = False
        self.img_scale_in_list = 'scale=0.5'
        self.img_scale_in_table = 'scale=0.2'
        self.parts_cntr = 1 #start numbering from 1
        self.tex_filename = ""
        self.tex_foldername = "chapters"
        self.fig_foldername = "figs"
        self.subfoldername = ""
        self.save_page_folder = "saved_pages"
        self.cur_book_part = book_part("")
        self.toc = []
        self.soup = BeautifulSoup("", 'html.parser')
        #self.page_url = input_url

    def download(self):
        '''
        Download lesson pages from www.imabi.net to
        When all pages are downloaded as html in saved_pages folder,
        this script can work offline by setting self.offline = True
        '''
        self.save_page_content('https://www.imabi.net/tableofcontents.htm')
        self.generate_toc()
        self.offline = False
        for book_part in self.toc:
            i = 0
            for chapter in book_part.chapters:
                i += 1
                print('Saving lesson (%d/%d) of part %s:%s'%(i,len(book_part.chapters),book_part.name,chapter))
                self.save_page_content(chapter)

    def generate_toc(self):
        '''
        Generate Table of Contents
        '''
        page_content = self.read_page_content('https://www.imabi.net/tableofcontents.htm')
        self.toc = []
        self.read_toc(page_content)
        self.toc.append(self.cur_book_part) #add last part

    def generate_chapter(self, page_url):
        '''
        Generate .tex file for one chapter from given page URL
        '''
        if self.subfoldername == "":
            for i in range(len(self.toc)):
                found = False
                for k in range(len(self.toc[i].chapters)):
                    if self.toc[i].chapters[k] == page_url:
                        #print('Part ID found:',i+1)
                        self.subfoldername = u'第%d章'%(i+1)
                        self.tex_filename = path.splitext(path.basename(page_url))[0] #u'第%d課:_'%(k+1) +
                        found = True
                        break
                if found:
                    break
        page_content = self.read_page_content(page_url)
        result = self.read_tag(page_content)
        if result is not None:
            print('   Parsing html tags were successful')
        else:
            print('   Parsing failed')
            return
        #result = self.handle_special_chars(result)
        self.save_output(result)

    def generate_part(self, part_id):
        '''
        Generate .tex file for Table Of Contents's part_id'th part
        '''
        print('Generating .tex file for part:',self.toc[part_id].name)
        #Prepare directory
        self.subfoldername = u'第%02d章'%(part_id+1)
        result = []
        #Add latex part hierarchy
        tmp = u'\n\\part{%s}\n'%(self.toc[part_id].name)
        result.append(tmp)
        processed = 0
        for chapter_url in self.toc[part_id].chapters:
            print('\nNow processing: [%s][%d/%d]'%(self.toc[part_id].name, processed+1,len(self.toc[part_id].chapters)))
            print('   Lesson from: %s'%(chapter_url))
            #Add each lesson as a latex chapter
            #self.tex_filename =  u'第%d課:_'%(processed+1) + path.splitext(path.basename(chapter_url))[0]
            self.tex_filename = path.splitext(path.basename(chapter_url))[0]
            self.generate_chapter(chapter_url)
            tmp = u'\n%% %s\n \\input{%s/%s/%s.tex}\n'%(chapter_url,self.tex_foldername, self.subfoldername, self.tex_filename)
            result.append(tmp)
            processed += 1
        self.tex_filename = self.handle_filename(self.subfoldername + ':_' + self.toc[part_id].name)
        self.subfoldername = ""
        result_ = "".join(result)
        self.save_output(result_)

    def generate_body(self):
        '''
        Generate .tex for including previously generated .tex files for parts
        '''
        result = []
        tex_folder = path.join(path.sep, os.getcwd(), self.tex_foldername)
        for filename in sorted(os.listdir(tex_folder)):
            if path.isfile(path.join(tex_folder, filename)):
                name, ext = path.splitext(filename)
                #generated file should be something like: 第?章:_?????.tex
                if '第' in name and ext == '.tex':
                    tmp = u'\n\\input{%s/%s}\n'%(self.tex_foldername, filename)
                    result.append(tmp)
        self.subfoldername = ""
        self.tex_foldername = ""
        self.tex_filename = self.handle_filename("imabi_body")
        result_ = "".join(result)
        self.save_output(result_)
        print('Done')

    def read_toc(self, tag):
        '''
        Read TOC page specific html tags
        '''
        for child_tag in tag.contents:
            if type(child_tag) is bs4.element.Tag:
                if child_tag.name == 'p' or child_tag.name == 'div':
                    if child_tag.has_attr('style'):
                        #Part names are centered
                        if child_tag.attrs['style'] == "text-align: center":
                            if self.cur_book_part.name != "":
                                self.toc.append(self.cur_book_part)
                            part_name = child_tag.getText().strip()
                            self.cur_book_part = book_part(part_name)
                            self.parts_cntr += 1;
                            continue
                        #Lesson names and corresponding URLs are left flushed
                        if child_tag.attrs['style'] == "text-align: left":
                            hlinks = child_tag.find_all('a', class_="fw_link_page")
                            for hlink in hlinks:
                                #Chapter will start with 第??課
                                if '第' in hlink.getText() and hlink.has_attr('href'):
                                    self.cur_book_part.chapters.append(hlink.attrs['href'])
                                    continue
                # Else unhandled tags
                self.read_toc(child_tag)

    def read_tag(self, tag):
        '''
        Read lessons page specific html tags
        '''
        result = []
        for child_tag in tag.contents:

            if type(child_tag) is bs4.element.NavigableString:
                tmp = r'%s '%(self.handle_special_chars(child_tag.string.strip()))
                result.append(tmp)

            if type(child_tag) is bs4.element.Tag:

                #Paragraph
                if child_tag.name == 'p':
                    if child_tag.getText().strip():
                        if self.inside_list is False and self.inside_table is False:
                        #if True:
                            centered = False
                            if child_tag.has_attr('style'):
                                if child_tag.attrs['style'] == 'text-align: center':
                                    centered = True
                            #Centered paragraph
                            if centered == True:
                                #Centered and underlined = Sub section
                                '''
                                cu_txt = child_tag.find_all('u')
                                if len(cu_txt) > 0:
                                    tmp = u'\n\\subsection{%s}\n'%(self.read_tag(cu_txt[0]))
                                    result.append(tmp)
                                    continue
                                else:
                                '''
                                tmp = u'\n\\begin{center}\n%s\n\\end{center}\n'%(self.read_tag(child_tag))
                                result.append(tmp)
                                continue
                            #Normal paragraph
                            else:
                                #tmp = u'\\hfill\\break %s\n'%(self.read_tag(child_tag))
                                tmp = u'\n\\par{%s}\n'%(self.read_tag(child_tag))
                                result.append(tmp)
                                continue
                        else:
                            tmp = u'%s\n'%(self.read_tag(child_tag))
                            result.append(tmp)
                            continue

                #Line break
                if child_tag.name == 'br':
                    #tmp = u'\\\\\n'
                    tmp = u'\\hfill\\break\n'
                    result.append(tmp)
                    continue
                    #print(child_tag)

                #Header
                if child_tag.name == 'h3':
                    #Chapter will start with 第?課
                    str_content = child_tag.getText()
                    str_parts = re.split(':|：',str_content)
                    #str_parts = str_content.split(':')
                    # 第Lessonname課:Lesson short name:Lesson description
                    # Use middle for chapter name
                    chapter_name = ""
                    if(len(str_parts)>=2):
                        if str_parts[0].strip().startswith('第'): #and str_parts[0].strip().endswith('課'):
                            #print('Chapter No:%s'%(str_parts[0][1:3]))
                            chapter_name = str_parts[1].strip()
                            for i in range(2,len(str_parts)-1):
                                #print('str_parts%d:%s'%(i,str_parts[i]))
                                chapter_name = chapter_name + str_parts[i]
                            if(str_parts[0][1:3] == '??'):
                                tmp = u'\n\\chapter*{%s}\n'%(self.handle_special_chars(chapter_name) )
                            else:
                                tmp = u'\n\\chapter{%s}\n'%(self.handle_special_chars(chapter_name) )
                            tmp = tmp + u'\n\\begin{center}\n\\begin{Large}\n%s\n\\end{Large}\n\\end{center}\n'%(self.handle_special_chars(str_content) )
                            self.tex_filename = self.handle_filename(str_parts[0]) + ':_' + self.tex_filename
                            result.append(tmp)
                            continue
                    #Section otherwise
                    tmp = u'\n\\section{%s}\n'%(self.handle_special_chars(str_content.strip()))
                    result.append(tmp)
                    continue

                #Italic text
                if child_tag.name == 'i':
                    tmp = u'\\emph{%s}'%(self.read_tag(child_tag))
                    result.append(tmp)
                    continue

                #Bold text
                if child_tag.name == 'b':
                    tmp = u'\\textbf{%s}'%(self.read_tag(child_tag))
                    result.append(tmp)
                    continue

                #Hyperlink
                if child_tag.name == 'a':
                    #print(child_tag)
                    #tmp = self.handle_url(self.read_tag(child_tag))
                    tmp = u'%s '%(self.read_tag(child_tag))
                    result.append(tmp)
                    continue
                '''
                #Font size
                if child_tag.name == 'font':
                    if child_tag.has_attr('size'):
                        # Small-2 Normal-3
                        if child_tag.attrs['size'] == '2':
                            tmp = u'\n\\begin{small}\n%s\n\\end{small}\n'%(self.read_tag(child_tag))
                            result.append(tmp)
                            continue
                        if child_tag.attrs['size'] == '3':
                            tmp = u'%s'%(self.read_tag(child_tag))
                            result.append(tmp)
                            continue
                '''

                #Kanji reading displayed over its character
                if child_tag.name == 'ruby':
                    kanji_char = ""
                    kanji_reading = ""
                    #print(child_tag)
                    for item in child_tag.contents:
                        #Kanji in normal text
                        if type(item) is bs4.element.NavigableString:
                            kanji_char = kanji_char + (u'%s'%(self.handle_special_chars(item.string.strip())))
                        if type(item) is bs4.element.Tag:
                            #Kanji in colored text
                            if item.name == 'span':
                                kanji_char = kanji_char + ('%s'%(self.handle_special_chars(item.getText().strip())))
                            #Kanji reading
                            if item.name == 'rt':
                                kanji_reading = kanji_reading + (r'%s'%(self.handle_special_chars(item.getText().strip())))
                    tmp = u'${\\overset{\\textnormal{%s}}{\\text{%s}}}$ '%(kanji_reading, kanji_char)
                    result.append(tmp)
                    continue

                #Unordered list
                if child_tag.name == 'ul':
                    if len(child_tag.find_all('li')) > 0 and self.inside_table is False:
                        self.inside_list = True
                        tmp = u'\n\\begin{itemize}\n%s\n\\end{itemize}\n'%(self.read_tag(child_tag))
                        self.inside_list = False
                        result.append(tmp)
                        continue

                #Ordered list
                if child_tag.name == 'ol':
                    if len(child_tag.find_all('li')) > 0 and self.inside_table is False:
                        self.inside_list = True
                        tmp = u'\n\\begin{enumerate}\n%s\n\\end{enumerate}\n'%(self.read_tag(child_tag))
                        self.inside_list = False
                        result.append(tmp)
                        continue

                #List item
                if child_tag.name == 'li':
                    if self.inside_list is True:
                        tmp = u'\n\\item %s'%(self.read_tag(child_tag))
                        result.append(tmp)
                        continue
                    if self.inside_table is True:
                        tmp = u'\n\\par{%s}\n'%(self.read_tag(child_tag))
                        result.append(tmp)
                        continue

                #Image
                if child_tag.name == 'img':
                    tmp = self.handle_image(child_tag)
                    result.append(tmp)
                    continue

                #Table
                if child_tag.name == 'table':
                    tmp = self.handle_table(child_tag)
                    result.append(tmp)
                    continue

                #Table row
                if child_tag.name == 'tr':
                    self.table_cell_cntr = 0
                    #self.table_row_sep = self.table_row_sep +
                    tmp = u'\n%s\n'%(self.read_tag(child_tag))
                    result.append(tmp)
                    continue

                #Table cell
                if child_tag.name == 'td':
                    cell_content = self.read_tag(child_tag)
                    #print('cell:',self.table_cell_cntr)
                    #Check if it is last element in a row
                    #col_separator = u' '

                    #Is it last cell in a row? if yes add \\ else add &
                    if child_tag.nextSibling is None:
                        col_separator = u'\\\\'
                    else:
                        if type(child_tag.nextSibling) == bs4.element.NavigableString and child_tag.nextSibling.nextSibling is None:
                            col_separator = u'\\\\'
                        else:
                            col_separator = u'& '

                    #Handle multicolumns
                    if child_tag.has_attr('colspan'):
                        col_width = int(child_tag.attrs['colspan'])
                        self.table_cell_cntr += col_width-1
                        #table_format = self.table_col_sep
                        #for i in range(col_width):
                        #    table_format += "P" + self.table_col_sep
                        tmp = u'\\multicolumn{%d}{|c|}{%s}'%(col_width,cell_content)
                    else:
                        #Handle multirows
                        if child_tag.has_attr('rowspan'):
                            row_height = int(child_tag.attrs['rowspan'])
                            #self.mr_location = self.table_cell_cntr
                            self.table_mrows.append(multi_row(row_height,self.table_cell_cntr,self.table_row_cntr))
                            tmp = u'\\multirow{%d}*{%s}'%(row_height,cell_content)
                        else:
                            tmp = cell_content

                    #Add additional col separator for multirows spanning in next row
                    missing_cell_filler = ""
                    for mrow in self.table_mrows:
                        if (self.table_cell_cntr + 1) == mrow.loc_x:
                            missing_cell_filler = missing_cell_filler + u' & '

                    #In case of last cell in a row, place row separater
                    if(col_separator == u'\\\\'):
                        #print('\nLine at:', self.table_row_cntr)
                        mrow_cells = [] #multirow cells that doesn't need row separater
                        for mrow in self.table_mrows[:]:
                            #print('mrow:x:%d y:%d h:%d'%(mrow.loc_x,mrow.loc_y, mrow.height))
                            if self.table_row_cntr == (mrow.loc_y + mrow.height - 1):
                                self.table_mrows.remove(mrow)
                            if self.table_row_cntr < (mrow.loc_y + mrow.height - 1):
                                mrow_cells.append(mrow.loc_x)
                        cur_pos = 1
                        for mrow_cell in mrow_cells:
                            col_separator = col_separator + ' \\cline{%d-%d}'%(cur_pos,mrow_cell)
                            cur_pos = mrow_cell+1
                        if cur_pos < self.table_width:
                            col_separator = col_separator + ' \\cline{%d-%d}'%(cur_pos,self.table_width)
                        self.table_row_cntr += 1

                    tmp = tmp + missing_cell_filler + col_separator
                    result.append(tmp)
                    self.table_cell_cntr += 1
                    continue

                # Else unhandled tags
                tmp = u'%s'%(self.read_tag(child_tag))
                result.append(tmp)
        return "".join(result)

    def handle_special_chars(self, input_str):
        '''
        Replace special characters with its equal latex escape strings
        '''
        out_str = input_str.replace('%', '\%')
        out_str = out_str.replace('{', '\\{')
        out_str = out_str.replace('}', '\\}')
        out_str = out_str.replace('｛', '\\{')
        out_str = out_str.replace('｝', '\\}')
        out_str = out_str.replace('&', '\\&')
        out_str = out_str.replace('$', '\\$')
        out_str = out_str.replace('#', '\\#')
        out_str = out_str.replace('_', '\\_ ')
        out_str = out_str.replace('^', '\\^{}')
        out_str = out_str.replace('/', '\\slash ')
        out_str = out_str.replace('’', '\\textquotesingle ')
        out_str = out_str.replace('→', '\\textrightarrow ')
        #out_str = out_str.replace('\'', '\\textquotesingle ')
        out_str = out_str.replace('...', '\\dothyp{}\\dothyp{}\\dothyp{}') #For allowing hyphenation with dots
        out_str = out_str.replace('　・', '\\hfill\\break\n・') #For listings started with dots
        out_str = out_str.replace('\% 第', '% 第')
        out_str = out_str.replace('\% h', '% h')
        out_str = self.handle_url(out_str)
        #out_str = out_str.replace('_', '\\_')
        #Replace chars in necessary places
        #out_str = out_str.replace('\\\\&', '&')
        #out_str = out_str.replace('\\\\$', '$')
        #tmp = tmp.replace('(', '\\-(') #For better hyphenation
        #tmp = tmp.replace('.', '\\-.') #For better hyphenation

        return out_str

    def handle_filename(self, filename):
        '''
        Replace URL encodings and other characters not supported in Latex normal text
        '''
        filename = filename.strip()
        filename = filename.replace(' ', '_')
        filename = filename.replace(' ', '_')
        filename = filename.replace('/', '_')
        filename = filename.replace('-', '_')
        filename = filename.replace('"', '')
        filename = filename.replace('&', 'and')
        filename = filename.replace('%20', '_')
        filename = filename.replace('%27', '_')
        filename = filename.replace('%28', '(')
        filename = filename.replace('%29', ')')
        return filename

    def handle_table(self, table_tag):
        '''
        Convert table tag to its latex equivalent
        '''
        self.table_row_cntr = 0
        has_border = True
        if table_tag.has_attr('border'):
            if table_tag.attrs['border'] == '0':
                if table_tag.has_attr('bgcolor'):
                    has_border = True
                else:
                    has_border = False

        #Can't hanlde table inside table
        if self.inside_table == True:
            has_border = False

        #Handle tables without border as normal paragraph
        if has_border is False:
            tmp = ""
            for cell in table_tag.find_all('td'):
                tmp = tmp + self.read_tag(cell)
            return tmp

        n_row = len(table_tag.find_all('tr'))
        n_element = len(table_tag.find_all('td'))

        n_col_max = 0;
        for row_ in table_tag.find_all('tr'):
            n_col = 0
            for cell in row_.contents:
                if cell.name == 'td':
                    if cell.has_attr('colspan'):
                        n_col += int(cell.attrs['colspan'])
                    else:
                        n_col += 1
            if n_col > n_col_max:
                n_col_max = n_col

        self.table_width = n_col_max

        table_format = '|'
        for i in range(self.table_width):
            table_format += "P|" # P -> Long tabulary table

        self.inside_table = True
        tmp = self.read_tag(table_tag)
        self.inside_table = False
        self.table_width = 0

        tmp = u'\n\\begin{ltabulary}{%s}\n\\hline \n%s\n\\end{ltabulary}\n'%(table_format, tmp)
        return tmp

    def handle_image(self, image_tag):
        '''
        Convert image tag to its latex equivalent
        '''
        if image_tag.has_attr('src'):
            img_url = image_tag.attrs['src']
        else:
            print('Img src was not given by html tag')
            return ""
        response = requests.get(img_url)
        if response.status_code == 200:
            downloaded_img = Image.open(io.BytesIO(response.content))
            img_filename = self.handle_filename(path.splitext(path.basename(img_url))[0])
            img_folder = self.tex_filename + '_fig' #Use subfolder for each chapter's images
            if not path.exists(path.join(path.sep, os.getcwd(), self.fig_foldername, self.subfoldername, img_folder)):
                os.makedirs(path.join(path.sep, os.getcwd(), self.fig_foldername, self.subfoldername, img_folder))
            img_filename = img_filename + '.png' #Convert to png
            downloaded_img.save(path.join(path.sep, os.getcwd(), self.fig_foldername, self.subfoldername, img_folder, img_filename),'png')
            if self.inside_list is True:
                tmp = u'\n\\includegraphics[%s]{%s/%s/%s/%s}\n'%(self.img_scale_in_list,self.fig_foldername, self.subfoldername, img_folder, img_filename)
            else:
                if self.inside_table is True:
                    tmp = u'\n\\includegraphics[%s]{%s/%s/%s/%s}\n'%(self.img_scale_in_table,self.fig_foldername, self.subfoldername, img_folder, img_filename)
                else:
                    tmp = u'\n\\includegraphics[width=0.9\\textwidth]{%s/%s/%s/%s}\n'%(self.fig_foldername, self.subfoldername, img_folder, img_filename)
                    tmp = u'\n\\begin{figure}[h]\n\\centering\n%s\n\\end{figure}\n'%(tmp)
            return tmp
        else:
            print('Cannot download img:',img_url)
            return ""

    def handle_url(self, input_str):
        '''
        Wrap URLs with latex inline equation keyword $
        '''
        tmp = input_str
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', tmp)
        if len(urls) > 0:
            #print('before:',tmp)
            for url in urls:
                tmp = tmp.replace(url, '\\url{%s}'%(url))
            #print('after:',tmp)
        return tmp

    def read_page_content(self, page_url):
        '''
        Read web page and return its main column
        whose ID is 'fw-mainColumn'
        '''
        if self.offline:
            html = open(self.save_page_folder + '/' + path.basename(page_url)).read()
        else:
            req = requests.get(page_url, verify=True)
            if req.status_code == 200:
                print('   Read page successful')
                html = req.text
            else:
                print('   Read page failed:%s'%(page_url))
                return None
        self.soup = BeautifulSoup(html, 'html.parser')
        mainCols = self.soup.find_all('div', { "class" : "webs-main" })
        if len(mainCols) > 0:
            print('   Found main paragraph')
            return mainCols[0]
        else:
            return None

    def save_page_content(self, page_url):
        '''
        Save web page as htm file
        Outputs are:
         <page_name>.htm original file
         <page_name>_pr.htm original file with added indentations for easier reading
        '''
        req = requests.get(page_url, verify=True)
        if req.status_code == 200:
            print('Read page successful')
        else:
            print('Read page failed:%s'%(page_url))
        soup = BeautifulSoup(req.text, 'html.parser')
        save_filename = self.save_page_folder + '/' + path.basename(page_url)
        if not path.exists(path.join(path.sep, os.getcwd(), self.save_page_folder)):
            os.makedirs(path.join(path.sep, os.getcwd(), self.save_page_folder))
        text_file = open(save_filename, "w")
        text_file.write("%s" % str(soup)) #.prettify()
        text_file.close()
        save_filename = self.save_page_folder + '/' + path.splitext(path.basename(page_url))[0] + '_pr' + path.splitext(path.basename(page_url))[1]
        text_file = open(save_filename, "w")
        text_file.write("%s" % str(soup.prettify())) #.prettify()
        text_file.close()
        print('Save page successful')

    def save_output(self, result):
        '''
        Save conversion result to .tex file:
        Filename: .<self.tex_foldername>/self.subfoldername>/<self.tex_filename>.tex
        '''
        if not path.exists(path.join(path.sep, os.getcwd(), self.tex_foldername, self.subfoldername)):
            os.makedirs(path.join(path.sep, os.getcwd(), self.tex_foldername, self.subfoldername))
        out_filename = u'%s/%s.tex'%(path.join(path.sep, os.getcwd(), self.tex_foldername, self.subfoldername),self.tex_filename)
        #out_filename = path.join(path.sep, os.getcwd(), self.tex_foldername, self.subfoldername) + '/' + self.tex_filename + '.tex'
        out_file = open(out_filename, "w")
        out_file.write("%s" %(result))
        out_file.close()
        print('Generated output file: %s'%(path.relpath(out_filename)))

def print_help():
    print('Usage: parser.py <options>...')
    print('Convert www.imabi.net contents to .tex filename')
    print('  -h, --help')
    print('      Show usage and help')
    print('  -l, --list')
    print('      Show available parts')
    print('  -d, --download')
    print('      Download lesson pages listed in Table of Contents page')
    print('  -s, --save <URL>')
    print('      Save web page as a html in saved_pages folder')
    print('  -c, --chapter <URL>')
    print('      Generate .tex file for the lesson of given URL')
    print('  -p, --part <part_id>')
    print('      Generate .tex file for the lessons of selected part')
    print('  -p, --part <start_id> <end_id>')
    print('      Generate .tex file for the lessons of selected parts')
    print('  -a, --all')
    print('      Generate .tex file for all lessons')

def parse_arguments():
    if len(sys.argv) == 2:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print_help()
            return

        if sys.argv[1] == "--list" or sys.argv[1] == "-l":
            my_converter = imabi_converter()
            my_converter.generate_toc()
            print('Available parts:')
            for p in my_converter.toc:
                print(p.name)
            return

        if sys.argv[1] == "--all" or sys.argv[1] == "-a":
            my_converter = imabi_converter()
            my_converter.generate_toc()
            for idx in range(len(my_converter.toc)):
                my_converter.generate_part(idx)
            my_converter.generate_body()
            return
        if sys.argv[1] == "--download" or sys.argv[1] == "-d":
            my_converter = imabi_converter()
            my_converter.download()
            return

    if len(sys.argv) == 3:
        if sys.argv[1] == "--part" or sys.argv[1] == "-p":
            idx = int(sys.argv[2])
            my_converter = imabi_converter()
            my_converter.generate_toc()
            if idx >0 and idx <= len(my_converter.toc):
                my_converter.generate_part(idx-1)
                my_converter.generate_body()
            else:
                print('Index out of range.')
                print('List available parts with --list or -l option.')
            return
        if sys.argv[1] == "--save" or sys.argv[1] == "-s":
            page_url = sys.argv[2]
            my_converter = imabi_converter()
            my_converter.save_page_content(page_url)
            return
        if sys.argv[1] == "--chapter" or sys.argv[1] == "-c":
            page_url = sys.argv[2]
            my_converter = imabi_converter()
            my_converter.generate_toc()
            my_converter.generate_chapter(page_url)
            return

    if len(sys.argv) == 4:
        if sys.argv[1] == "--part" or sys.argv[1] == "-p":
            start_idx = int(sys.argv[2])
            end_idx = int(sys.argv[3])
            my_converter = imabi_converter()
            my_converter.generate_toc()
            if start_idx >0 and start_idx <= len(my_converter.toc) and end_idx >0 and end_idx <= len(my_converter.toc):
                #my_converter.generate_part(idx)
                for idx in range(start_idx, end_idx+1):
                    my_converter.generate_part(idx-1)
                my_converter.generate_body()
            else:
                print('Index out of range.')
                print('List available parts with --list or -l option.')
            return

    print_help()

if __name__ == "__main__":
  #Run as main program
  parse_arguments()
