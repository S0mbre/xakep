# -*- coding: utf-8 -*-
"""
Created on Fri Apr  6 11:43:21 2018

@author: Искандер
"""

import requests, re, sys

def down(url, rootdir, auth=None, cookiejar=None):
    try:        
        #print(cookiejar)
        h = requests.head(url, allow_redirects=True, auth=auth, cookies=cookiejar)
        header = h.headers
        """
        content_type = header.get('content-type')
        if 'text' in content_type.lower() or 'html' in content_type.lower():
           return '!!! URL {} HAS NO DOWNLOADABLE CONTENT!'.format(url)
        """
        
        print(header)
       
        try:
            fname = re.findall('filename=(.+)', header['content-disposition'])
            if not fname: raise Exception
        except:
            return '!!! COULD NOT GET FILENAME FROM {}'.format(url)
        
        res = requests.get(url, allow_redirects=True, auth=auth, cookies=cookiejar)
            
        if not res: return '!!! COULD NOT DOWNLOAD {}'.format(url) 
        
    except Exception as err:
        return '!!! COULD NOT DOWNLOAD {}\n{}'.format(url, str(err))
    
    file = '{}\\{}'.format(rootdir, fname)
    
    try:
        with open(file, 'wb') as outfile:
            outfile.write(res.content)
    except:
        return '!!! COULD WRITE TO {}'.format(file)
        
    return '{} >> {}'.format(url, file)
            
def mass_down(url_file, rootdir, auth=None):
    
    s = requests.Session()
    
    if auth:        
        s.post('https://xakep.ru/wp-login.php', {'log': auth[0], 'pwd': auth[1], 'testcookie': 1})
    
    with open(url_file, 'r', encoding='utf-8') as infile:
        for line in infile:
            try:
                r = down(line.strip(), rootdir, cookiejar=s.cookies)
                print(r)
            except KeyboardInterrupt:
                return
            
def main():
    if len(sys.argv) != 3 and len(sys.argv) != 5:
        print('USAGE:\n{} {} {} [{} {}]'.format(sys.argv[0], 'url file', 'root directory', 'site login (OPTIONAL)', 'site password (OPTIONAL)'))
        return
    
    auth = (sys.argv[3], sys.argv[4]) if len(sys.argv) == 5 else None
    
    mass_down(sys.argv[1], sys.argv[2], auth)

if __name__ == '__main__':
    main()
    