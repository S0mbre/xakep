# -*- coding: utf-8 -*-
"""
Created on Fri Nov 10 10:29:46 2017

@author: isshafikov
"""

from os import path
import sqlite3
import re

#-------------------- CONST --------------------
SQL_MAX_ROWS = 1000
SQL_TABLES = ['xkissues', 'xkcovers', 'xkcontent']
SQL_xkissues_cols = ['id_iss', 'title', 'nissue', 'published', 'pdf_url', 'info_url']
SQL_xkcovers_cols = ['id_cov', 'id_iss2', 'cover_width', 'cover_url']
SQL_xkcontent_cols = ['id_cont', 'id_iss3', 'art_cat', 'art_lev1', 'art_lev2', 'art_desc']

SQL_str_replacements = {"'": "’"}

SQL_CLEAR =\
"""
DROP TABLE IF EXISTS xkcovers;
DROP TABLE IF EXISTS xkcontent;
DROP TABLE IF EXISTS xkissues;
"""

SQL_FIND_ISSUES1 =\
r"""
select xkissues.*, xkcontent.*
from xkcontent
inner join xkissues on xkissues.id_iss = xkcontent.id_iss3
where xkcontent.art_lev1 regexp "{0}" or xkcontent.art_lev2 regexp "{0}" or xkcontent.art_desc regexp "{0}"
order by {1} {2};
"""

SQL_CREATE =\
"""
DROP TABLE IF EXISTS xkcovers;
DROP TABLE IF EXISTS xkcontent;
DROP TABLE IF EXISTS xkissues;

CREATE TABLE xkissues (
    id_iss INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT DEFAULT '',
    nissue INTEGER DEFAULT 0,
    published TEXT DEFAULT '', 
    pdf_url TEXT DEFAULT '',
    info_url TEXT DEFAULT ''
);

CREATE TABLE xkcovers (
    id_cov INTEGER PRIMARY KEY AUTOINCREMENT,
    id_iss2 INTEGER REFERENCES xkissues(id_iss) ON UPDATE CASCADE ON DELETE SET NULL,
    cover_width INTEGER DEFAULT 0,
    cover_url TEXT DEFAULT ''
);
 
CREATE TABLE xkcontent (
    id_cont INTEGER PRIMARY KEY AUTOINCREMENT,
    id_iss3 INTEGER REFERENCES xkissues(id_iss) ON UPDATE CASCADE ON DELETE SET NULL,
    art_cat TEXT DEFAULT '',
    art_lev1 TEXT DEFAULT '',
    art_lev2 TEXT DEFAULT '',
    art_desc TEXT DEFAULT ''
);
"""
#------------------------------------------------

def regexp(expr, item):
    reg = re.compile(expr)
    return reg.search(item) is not None

class tsqlite(object):
    """
    """
    def __init__(self, sqldbfile='', opendb=True, forcecreate=False):
        self.SQL_CON = None
        self.SQL_CUR = None        
        self.SQLDB = sqldbfile
        self.__chunkflag = False
        if opendb: self.opendb(forcecreate)  
    
    def __del__(self):
        self.closedb()
        
    def connect(self, forceconnect=False):
        if not forceconnect and self.check_conn(): return {}         
        self.SQL_CON = sqlite3.connect(self.SQLDB)
        self.SQL_CON.create_function('REGEXP', 2, regexp)
        self.SQL_CUR = self.SQL_CON.cursor()  
        
    def check_conn(self):
        return bool(self.SQL_CUR)
    
    def commit(self):
        if self.SQL_CON: self.SQL_CON.commit() 
        
    def rollback(self):
        if self.SQL_CON: self.SQL_CON.rollback()  
    
    def recreate_db(self):
        self.opendb(True) 
        
    def clear_db(self):
        self.connect()
        self.SQL_CUR.executescript(SQL_CLEAR)
    
    def opendb(self, forcecreate=False):
        """
        """
        db_existed = path.isfile(self.SQLDB)
        self.connect(True)
        if not db_existed or forcecreate:               
            self.SQL_CUR.executescript(SQL_CREATE)
        
    def closedb(self, commitall=True):  
        """
        """            
        if self.SQL_CUR: 
            self.SQL_CUR.close()    # Закрываем объект-курсора
            self.SQL_CUR = None
            
        if self.SQL_CON: 
            if commitall:
                self.SQL_CON.commit()
            else:
                self.SQL_CON.rollback()
                
            self.SQL_CON.close()    # Закрываем соединение
            self.SQL_CON = None
        
    def sql_format_str(self, string):
        st = string
        for k, v in SQL_str_replacements.items():
            st = st.replace(k, v)
        return st
        
    def insert_issue_record(self, d_issue, commit=False):
        """
        Добавляет в БД записи с данными по выпуску: метаданные и содержание.
        """
        self.connect()
    
        self.SQL_CUR.execute("INSERT INTO xkissues({}) VALUES ('{}', {}, '{}', '{}', '{}');".format(', '.join(SQL_xkissues_cols[1:]), \
            self.sql_format_str(d_issue['title']) if 'title' in d_issue else '', \
            d_issue['number'] if 'number' in d_issue else 0, \
            self.sql_format_str(d_issue['published']) if 'published' in d_issue else '', \
            self.sql_format_str(d_issue['pdf']) if 'pdf' in d_issue else '', \
            self.sql_format_str(d_issue['url']) if 'url' in d_issue else ''))
        
        self.SQL_CUR.execute("SELECT last_insert_rowid() FROM xkissues;")
        id_issue = self.SQL_CUR.fetchone()
        if id_issue:
            id_issue = int(id_issue[0])
        else:
            return {'Error': 'Невозможно получить ID последней записи!'}
        
        for hsz in d_issue['cover']:
            self.SQL_CUR.execute("INSERT INTO xkcovers({}) VALUES ({}, {}, '{}');".format(', '.join(SQL_xkcovers_cols[1:]), \
                            id_issue, hsz, d_issue['cover'][hsz]))
            
        for cat_name in d_issue['content']:
            for ls_art in d_issue['content'][cat_name]: 
                self.SQL_CUR.execute("INSERT INTO xkcontent({}) VALUES ({}, '{}', '{}', '{}', '{}');".format(', '.join(SQL_xkcontent_cols[1:]), \
                                id_issue, self.sql_format_str(cat_name), \
                                self.sql_format_str(ls_art[0]), \
                                self.sql_format_str(ls_art[1]), \
                                self.sql_format_str(ls_art[2])))
           
        if commit: self.SQL_CON.commit()
        
        return {}
    
    def exec_sql(self, sql, commit=False):
        """
        """
        self.connect()
        self.SQL_CUR.executescript(sql)
        if commit: self.SQL_CON.commit()
    
    def select(self, sql, maxrows=SQL_MAX_ROWS, newselect=True, fieldnames=True):
        """
        """   
        if newselect:
            self.__chunkflag = False        
            
        if not self.__chunkflag or maxrows < 0:
            self.connect()
            self.SQL_CUR.execute(sql)
            
        if maxrows < 0:
            res = self.SQL_CUR.fetchall()
            if fieldnames and self.SQL_CUR.description:
                res.insert(0, tuple(description[0] for description in self.SQL_CUR.description))
            return res
        
        res = self.SQL_CUR.fetchmany(maxrows) 
        if fieldnames and self.SQL_CUR.description and not self.__chunkflag:
            res.insert(0, tuple(description[0] for description in self.SQL_CUR.description))
        self.__chunkflag = bool(res)            
        return res
    
    def _permute_keyword(self, kw):
        """
        """
        ls = [kw.upper(), kw.lower()]
        if len(kw) > 1:
            ls.append(kw[0].upper() + kw[1:].lower())
        return ls
    
    def get_issues_by_content(self, keyword, orderby='xkissues.nissue', ordering='desc', **kwargs):
        """
        """
        return self.select(SQL_FIND_ISSUES1.format('|'.join(self._permute_keyword(keyword)), orderby, ordering), **kwargs)
            
    def insert_issue_records(self, d_issues, commit=False, on_before_insert=None, on_insert=None, on_error=None):
        """
        """
        for dres in d_issues:
            if on_before_insert: on_before_insert(self, dres)
            ins_res = self.insert_issue_record(dres) 
            if on_insert and not ins_res: on_insert(self, dres)
            if on_error and ins_res: on_error(self, dres, ins_res['Error'])
            
        if commit: self.SQL_CON.commit()
        
    def get_issue_count(self):
        """
        """
        self.connect()
        self.SQL_CUR.execute("SELECT count({}) FROM xkissues;".format(SQL_xkissues_cols[0]))
        n_issues = self.SQL_CUR.fetchone()
        if n_issues:
            return int(n_issues[0])
        else:
            return {'Error': 'Невозможно получить ID последней записи!'}
    
    def get_last_issue_number(self):
        """
        """
        self.connect()
        self.SQL_CUR.execute("SELECT max({}) FROM xkissues;".format(SQL_xkissues_cols[2]))
        n_issue = self.SQL_CUR.fetchone()
        if n_issue:
            return int(n_issue[0])
        else:
            return {'Error': 'Невозможно получить ID последней записи!'}       