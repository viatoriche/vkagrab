#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""VK Photo Albums grabber

Author:  Viator <viator@via-net.org>
License: GPL (see http://www.gnu.org/licenses/gpl.txt)
"""
import logging
import os
from grab import Grab
from grab import error as grab_errors
import re
from time import sleep
import sys

sys.setrecursionlimit(100000)

try:
    import config
    LOGIN = config.login
    PASSWORD = config.password
except:
    LOGIN = None
    PASSWORD = None

class VKG(Grab):
    """Grabber photo albums

    uid - from vk.com/->uid<-
    dest_dir - path/to/files
    """
    vkurl = u'http://m.vk.com/{}'
    denied_smbs = u'/\:*?«<>|'
    GROUP = 0
    USER = 1
    def __init__(self, grab_uid, dest_dir = None, log_dir = None,
                    login = None, password = None):
        self.grab_uid = grab_uid.decode('UTF-8')
        if dest_dir is not None:
            self.dest_dir = dest_dir.decode('UTF-8') + u'/{}'
        else:
            self.dest_dir = self.grab_uid + u'/{}'

        try:
            os.mkdir(self.dest_dir.format(''))
        except OSError:
            pass

        self.login = login
        self.password = password
        Grab.__init__(self)
        if log_dir is not None:
            self.setup(log_dir = log_dir)
        self.open_cache = False
        self.setup(hammer_mode=True, hammer_timeouts=((2, 5), (10, 15), (20, 30)))
        self.auth()

    def auth(self):
        """Auth VK
        """
        if self.login is not None and self.password is not None:
            print 'Auth with {}'.format(self.login)
            self.go('http://login.vk.com/?act=login')
            self.set_input('email', self.login)
            self.set_input('pass', self.password)
            self.set_input('expire', '')
            self.submit()

    #def go_vk(self, uri):
        #try:
            #self.go(self.vkurl.format(uri))
        #except grab_errors.GrabTimeoutError:
            #self.go_vk(self, uri)

    def go_vk(self, uri):
        self.go(self.vkurl.format(uri))

    def get_photo(self, name, start, uri, inc):
        print 'Download: ', inc, uri[1:]
        self.go_vk(uri[1:])

        try:
            actions = self.xpath_list('//*[@class="actions"]')[0].xpath('li')
        except IndexError:
            sleep(4)
            return self.get_photo(name, start, uri, inc)

        full_size_url = actions[-1:][0].xpath('a')[0].get('href')

        filename = os.path.basename(full_size_url)
        dest_file = u'{}/{}_{}'.format(self.dest_dir.format(name),
                                        inc, filename)

        try:
            next_uri = self.xpath_list('//*[@class="r"]')[0]\
                        .xpath('a')[0].get('href')
        except IndexError:
            next_uri = 'Done'

        try:
            open(dest_file, 'rb')
        except IOError:
            self.download(full_size_url, dest_file)

        if next_uri == 'Done':
            return 'Done'

        if next_uri != start:
            inc += 1
            return self.get_photo(name, start, next_uri, inc)
        else:
            return 'Done'

    def test_symbol(self, symbol):
        if symbol in self.denied_smbs:
            return '_'
        else:
            return symbol

    def normalize(self, name):
        return ''.join([self.test_symbol(symbol) for symbol in name])

    def get_album(self, name, uri, try_count = 0):
        if try_count == 5:
            return
        print 'Get album: ', name
        self.go_vk(uri[1:])
        try:
            photos = self.xpath_list('//*[@class="al_photo"]')
            uri = photos[0].get('href')
        except IndexError:
            sleep(4)
            try_count += 1
            self.get_album(name, uri, try_count)
            return
        self.get_photo(name, uri, uri, 1)

    def get_albums(self, id, variant = 0, offset = 0, cache_e = 0):
        print 'Get albums: ', id, offset

        if variant == self.GROUP:
            self.go_vk('albums-{}?offset={}'.format(id, offset))
        elif variant == self.USER:
            self.go_vk('albums{}?offset={}'.format(id, offset))

        albums = self.xpath_list('//*[@class="album"]')

        if albums == []:
            return 0

        for e, album in enumerate(albums):
            if e < cache_e:
                continue
            uri = album.xpath('a')[0].get('href')
            name = self.normalize(album.find_class('name')[0].text_content())
            try:
                os.mkdir(self.dest_dir.format(name))
            except OSError:
                pass
            self.save_cache(offset, e)
            self.get_album(name, uri)

        offset += 20
        return self.get_albums(id, variant, offset)

    def save_cache(self, offset, album):
        open('cache', 'w').write('{}:{}'.format(offset, album))

    def load_cache(self):
        if not self.open_cache:
            self.open_cache = True
            try:
                return map(lambda x: int(x), open('cache', 'r').read().split(':'))
            except IOError:
                return [0, 0]
        else:
            return [0, 0]

    def clear_cache(self):
        try:
            os.remove('cache')
        except OSError:
            pass

    def start(self):
        self.go_vk(self.grab_uid)
        offset, cache_e = self.load_cache()
        print offset, cache_e
        if self.response.code == 200:
            st = self.response.unicode_body()
            try:
                return self.get_albums(re.search(r'\"\/photos-(\d+)\"', st)\
                    .group(1), self.GROUP, offset, cache_e)
            except AttributeError:
                return self.get_albums(re.search(r'\"\/photos(\d+)\"', st)\
                    .group(1), self.USER, offset, cache_e)
        else:
            return 1

def test():
    logging.basicConfig(level=logging.DEBUG)
    vkg = VKG('id41180005', dest_dir = 'id41180005', log_dir = 'logs',
                login=LOGIN, password = PASSWORD)
    #vkg = VKG('ne2ch', dest_dir = 'ne2ch', log_dir = 'logs',
                #login=None, password = None)
    vkg.start()

def main():
    import sys
    args = sys.argv[1:]
    if args == []:
        print 'Usage: python vkagrab.py uid1[:dir1] ... uid_N[:dir_N]'
    for arg in args:
        arg = arg.split(':')
        uid = arg[0]
        if len(arg) > 1:
            dest_dir = arg[1]
        else:
            dest_dir = uid
        vkg = VKG(uid, dest_dir = dest_dir,
                    login = LOGIN, password = PASSWORD)
        vkg.start()
        vkg.clear_cache()

if __name__ == '__main__':
    #test()
    main()

# vi: ft=python:tw=0:ts=4

