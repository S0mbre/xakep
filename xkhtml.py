# -*- coding: utf-8 -*-
"""
Created on Fri Nov 10 10:26:47 2017

@author: isshafikov
"""

from bs4 import BeautifulSoup
import requests, json, re

#-------------------- CONST --------------------
URL_ISSUES = r'https://xakep.ru/issues/'                 # URL архива статей
URL_ISSUE_MASK = r'https://xakep.ru/issues/xa/{:03d}/'   # маска URL страницы выпуска, e.g. https://xakep.ru/issues/xa/223/
URL_PDF_MASK = r'https://xakep.ru/pdf/xa/{:03d}'         # маска URL для скачивания PDF выпуска, e.g. https://xakep.ru/pdf/xa/223
BSPARSER = 'html.parser'                                 # парсер для BS = HTML
BS_IMGCLASS = re.compile('attachment-full')              # для поиска тегов изображения обложки
BS_CONTID = 'issue-content'                              # для поиска контейнера содержания статей
BS_ISSUESCLASS = re.compile(r'/issues/xa/')              # для поиска последнего номера выпуска на главной странице
N_ISSUE_NEWCONTENTFORMAT = 211                           # номер выпуска, начиная с которого форматирование страницы отличается от предыдущих
#------------------------------------------------

class xakep(object):
    """
    """
    def __init__(self, xk_auth=None):
        self.xk_auth = xk_auth
        if not self.check_connection():
            raise Exception('Невозможно подключиться к серверу. Проверьте интернет соединение.')

    def check_connection(self):
        """
        Проверяет доступность интернет-соединения. 
        Возвращает True в случае наличия соединения и False при его отсутствии.
        """
        try:
            res = requests.get(URL_ISSUES, timeout=1000)
            return bool(res)        
        except:
            return False
        return False
    
    def getissue_info(self, n_issue, get_content=True):
        """
        Возвращает информацию для данного номера журнала в виде словаря:
        {
         title: 'Заголовок'
         number: номер_выпуска
         published: 'дата_выпуска'
         cover: {0: 'URL', ширина_пикс: 'URL', ...}
         pdf: 'URL PDF'
         url: 'URL страницы номера'
         content:
         {
          'category': [['заголовок', 'подзаголовок', 'описание'], ...],
           ...
         }
        }
         В возвращаемом словаре массив 'content' (содержание статей) выводится
         в результат только если get_content==True.
        """
        
        # качаем страницу с информацией о данном выпуске
        try:
            res = requests.get(URL_ISSUE_MASK.format(n_issue), auth=self.xk_auth)
        except requests.exceptions.RequestException as err:
            return {'Error': 'Невозможно выполнить запрос:\n{0}'.format(str(err))}
        except:
            return {'Error': 'Невозможно выполнить запрос.'}
        
        # если err != 200, возвращаем ошибку
        if res.status_code != 200:
            return {'Error': 'Невозможно получить страницу (HTML status = {0}).'.format(res.status_code)}
        
        # парсим HTML страницы супом
        try:
            soup = BeautifulSoup(res.text, BSPARSER)
        except Exception as err:
            return {'Error': 'Ошибка разбора страницы:\n{0}'.format(str(err))}
        
        # выдергиваем заглавие и номер
        dres = {'title': soup.title.string, 'number': n_issue}
        
        # тянем дату выпуска
        bs_date = soup.find('meta', attrs={'itemprop': 'datePublished'})
        if bs_date:
            dres['published'] = bs_date['content'].split('T')[0] or '' 
        else:
            dres['published'] = ''
        
        # создаем словарь для хранения URL обложек
        dres['cover'] = {}
        bs_img = soup.find('img', class_=BS_IMGCLASS)
        
        if bs_img:
            if 'src' in bs_img.attrs:
                # обложка по умолчанию
                dres['cover'][0] = bs_img['src']
            if 'srcset' in bs_img.attrs:
                # обложки разных размеров
                ls_urls = bs_img['srcset'].split(',')
                for st_url in ls_urls:
                    ls_url = st_url.strip().split(' ')
                    hsz = int(ls_url[1][:-1])
                    dres['cover'][hsz] = ls_url[0]
                    
        dres['pdf'] = URL_PDF_MASK.format(n_issue)     # ссылка на PDF
        dres['url'] = URL_ISSUE_MASK.format(n_issue)   # ссылка на страницу выпуска
        
        # создаем словарь для хранения содержания выпуска
        dres['content'] = {}
            
        if get_content:        
            bs_cont = soup.find('div', id=BS_CONTID) 
            if not bs_cont: return dres
            if n_issue < N_ISSUE_NEWCONTENTFORMAT:
                # до выпуска №211 форматирование было старым...
                for tag_h5 in bs_cont.find_all('h5'):
                    # рубрика
                    dres['content'][tag_h5.string] = []
                    tag_ul = tag_h5.find_next_sibling('ul')
                    if tag_ul:
                        for tag_li in tag_ul.find_all('li'):
                            # заголовок, подзаголовок и описание статьи (описания нет до 211 выпуска)
                            # (если нет чего-то, то пустая строка)
                            vals = ['', '', '']
                            tag_a = tag_li.find('a') or tag_li
                            if tag_a:
                                tag_li_0 = tag_a.find('strong')
                                if tag_li_0: vals[0] = tag_li_0.string
                                vals[1] = tag_a.text[len(vals[0]):]
                                if vals[1].startswith('. '): vals[1] = vals[1][2:] 
                            dres['content'][tag_h5.string].append(vals)
            else:
                # начиная с выпуска №211 форматирование стало другим...
                for tag_h2 in bs_cont.find_all('h2'):
                    # рубрика
                    dres['content'][tag_h2.string] = []    
                    for tag_art in tag_h2.find_next_siblings('div'):
                        # заголовок, подзаголовок и описание статьи
                        vals = ['', '', '']
                        tag_h3 = tag_art.find('h3')
                        if tag_h3: vals[0] = tag_h3.string
                        tag_h4 = tag_art.find('h4')
                        if tag_h4: vals[1] = tag_h4.string
                        tag_p = tag_art.find('p')
                        if tag_p: vals[2] = tag_p.string or ''
                        dres['content'][tag_h2.string].append(vals)
                        
        return dres 
    
    def getlastissue_number(self):
        """
        Получает номер последнего выпуска.
        """
        try:
            res = requests.get(URL_ISSUES, auth=self.xk_auth)
        except requests.exceptions.RequestException as err:
            return {'Error': 'Невозможно выполнить запрос:\n{0}'.format(str(err))}
        except:
            return {'Error': 'Невозможно выполнить запрос.'}
        
        if res.status_code != 200:
            return {'Error': 'Невозможно получить страницу (HTML status = {0}).'.format(res.status_code)}
        
        try:
            soup = BeautifulSoup(res.text, BSPARSER)
        except Exception as err:
            return {'Error': 'Ошибка разбора страницы:\n{0}'.format(str(err))}
        
        bs_last = soup.find('a', href=BS_ISSUESCLASS)
        if not bs_last:
            return {'Error': 'Невозможно найти тег на странице.'}    
        
        bs_last_str = bs_last['href']
        return int(bs_last_str.split('/')[-1]) # пока нет обработки ошибок...
    
    def print_issue_data(self, n_issue, get_content=True):
        """
        Выводит в консоль данные по указанному выпуску.
        """
        print(self.getissue_info(n_issue, get_content)) 
        
    def dump_issues_to_file(self, iss_data, dumpfile, overwrite=False):
        """
        """
        with open(dumpfile, 'w' if overwrite else 'a', encoding='utf-8') as outfile:
            json.dump(iss_data, outfile, ensure_ascii=False, indent=2, sort_keys=False)
            
    def get_issues_from_file(self, dumpfile):
        """
        """        
        with open(dumpfile, 'r', encoding='utf-8') as infile:     
            iss_data = json.load(infile)
        return iss_data or None
        
    def get_issues(self, n_issue_start=1, n_issue_end=-1, get_content=True, dumpfile=None):
        """
        Получает данные по указанным выпускам журнала (start...end) и опционально
        сохраняет в файл в формате JSON.
        """
        if n_issue_end < n_issue_start:
            n_issue_end = self.getlastissue_number()
        if n_issue_end - n_issue_start < 0:
            return {'Error': 'Диапазон для получения выпусков имеет отрицательную длину: [{} : {}]'.format(n_issue_start, n_issue_end)} 
        ls_data = [self.getissue_info(n_issue, get_content) for n_issue in range(n_issue_start, n_issue_end+1)]
        if dumpfile: self.dump_issues_to_file(ls_data, dumpfile, True)
        return ls_data
    
    def get_issues_iter(self, n_issue_start=1, n_issue_end=-1, get_content=True, dumpfile=None):
        """
        """
        if n_issue_end < n_issue_start:
            n_issue_end = self.getlastissue_number()
        for n_issue in range(n_issue_start, n_issue_end+1):
            iss_data = self.getissue_info(n_issue, get_content) 
            yield iss_data  
            if dumpfile: self.dump_issues_to_file(iss_data, dumpfile, False)
                
    def generate_pdf_urls(self, n_issue_start=1, n_issue_end=-1, dumpfile=None):
        """
        Генерирует список ссылок для скачивания журналов.
        """
        if n_issue_end < n_issue_start:
            n_issue_end = self.getlastissue_number()
        ls_urls = [URL_PDF_MASK.format(n_issue) for n_issue in range(n_issue_start, n_issue_end+1)]
        if dumpfile:
            with open(dumpfile, 'w', encoding='utf-8') as outfile:
                outfile.write('\n'.join(ls_urls))