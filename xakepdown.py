# -*- coding: utf-8 -*-
"""
Редактор Spyder

Это временный скриптовый файл.
"""

from xkhtml import xakep
from xksql import tsqlite
from os import getcwd
from time import sleep, time
import sys
import threading

DMPFILE = r'{}\xakepissues.txt'.format(getcwd())         # файл для сохранения данных по умолчанию
THREAD_CHUNK = 20
threads = []
ALL_ISSUES = []

def worker_parse_to_file(n_start, n_end, auth=None, dumpfile=None, update_array=False):
    """
    """ 
    global ALL_ISSUES
    
    xkparser = None
    start_time = time()
    try:
        xkparser = xakep(auth)
    except Exception as err:
        print(err)
        return
    
    if not xkparser: return

    lsdata = xkparser.get_issues(n_start, n_end, True)
    
    with threading.Lock():            
        if dumpfile: 
            xkparser.dump_issues_to_file(lsdata, dumpfile, False) 
        if update_array: 
            for dres in lsdata:
                ALL_ISSUES.append(dres)
        
    time_taken = time() - start_time
    
    print('СКАЧАНЫ ДАННЫЕ ПО ВЫПУСКАМ {:d} - {:d}\t\t\t\t[{:d} активных потоков] - [выполнено за {:.2f} с.]'.format(n_start, n_end, len(threading.enumerate()), time_taken))
    
def update_dumpfile(auth, dumpfile, fill_global_list=False):
    """
    """
    global threads

    xkparser = None
    try:
        xkparser = xakep(auth)
    except Exception as err:
        print(err)
        return
    
    if not xkparser: return

    n_end = xkparser.getlastissue_number()
    thr_cnt = n_end // THREAD_CHUNK  
    
    cur_threads = len(threading.enumerate())
    
    for n_thread in range(0, thr_cnt + 1):
        st = n_thread * THREAD_CHUNK + 1
        en = (n_thread + 1) * THREAD_CHUNK
        if en > n_end: en = n_end 
        next_thread = threading.Thread(target=worker_parse_to_file, args=(st, en, auth, dumpfile, fill_global_list))
        threads.append(next_thread)
        next_thread.start()
        
    try:
        while len(threading.enumerate()) > cur_threads:
            sleep(0.5)  
            
    except KeyboardInterrupt:
        print('!!! Waiting for running threads to finish ...')
        for next_thread in threads:
            next_thread.join()
        print('!!! STOPPED ALL THREADS.')
        raise
        
def on_before_insert_issue(xkdb_object, dres):
    """
    """
    print('>>> INSERTING iss. {:d}...\t\t\t\t'.format(dres['number']), end='')
        
def on_insert_issue(xkdb_object, dres):
    """
    """
    print('done iss. {:d}.'.format(dres['number']))
    
def on_error_insert_issue(xkdb_object, dres, err_message):
    """
    """
    print('!!! ERROR iss. {:d}: "{:s}"'.format(dres['number'], err_message))
    
def update_db(auth=None, clear_db=False):
    """
    """
    xkparser = None
    try:
        xkparser = xakep(auth)
    except Exception as err:
        print(err)
        return
    
    if not xkparser: return
    
    xkdb = tsqlite(r'{}\xakepdb.db'.format(getcwd()), True, clear_db)
    if not xkdb:
        print('Ошибка открытия / создания БД!')
        return
    else:
        print('*** Подключение к СУБД установлено. {:s}***'.format('БД очищена! ' if clear_db else ''))
        
    last_iss = 1
    if not clear_db:
        last_iss = xkdb.get_last_issue_number() 
        print('*** Последний выпуск в БД = {}'.format(last_iss))  

    d_issues = xkparser.get_issues(n_issue_start=1 if clear_db else last_iss + 1) 
    if isinstance(d_issues, dict) and 'Error' in d_issues:
        print(d_issues['Error'])
        return
    print('*** Скачаны с сайта данные по {} выпускам'.format(len(d_issues)))
   
    xkdb.insert_issue_records(d_issues, commit=True, on_before_insert=on_before_insert_issue, on_insert=on_insert_issue, on_error=on_error_insert_issue)
    print('*** СУБД обновлена! БД содержит {:d} выпусков. ***'.format(xkdb.get_issue_count()))

def main():
    """
    Главная функция.
    """    
    
    if len(sys.argv) != 1 and len(sys.argv) != 3:
        print('ИСПОЛЬЗОВАНИЕ:\n{} [{} {}]'.format(sys.argv[0], 'ЛОГИН (опционально)', 'ПАРОЛЬ (опционально)'))
        return

    auth = (sys.argv[1], sys.argv[2]) if len(sys.argv) == 3 else None
    update_db(auth)
    
if __name__ == '__main__':
    main()