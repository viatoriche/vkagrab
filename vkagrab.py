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

    def go_vk(self, uri):
        try:
            self.go(self.vkurl.format(uri))
        except grab_errors.GrabTimeoutError:
            self.go_vk(self, uri)

    def get_photo(self, name, start, uri, inc):
        print 'Download: ', inc, uri[1:]
        self.go_vk(uri[1:])

        try:
            actions = self.xpath_list('//*[@class="actions"]')[0].xpath('li')
        except IndexError:
            sleep(2)
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

    def get_photos(self, name, uri):
        print 'Get album: ', name
        self.go_vk(uri[1:])
        photos = self.xpath_list('//*[@class="al_photo"]')
        uri = photos[0].get('href')
        self.get_photo(name, uri, uri, 1)

    def get_albums(self, id, offset = 0, variant = 0):
        print 'Get albums: ', id, offset
        if variant == self.GROUP:
            self.go_vk('albums-{}?offset={}'.format(id, offset))
        elif variant == self.USER:
            self.go_vk('albums{}?offset={}'.format(id, offset))
        offset += 20
        albums = self.xpath_list('//*[@class="album"]')
        if albums == []:
            return 0
        for album in albums:
            uri = album.xpath('a')[0].get('href')
            name = self.normalize(album.find_class('name')[0].text_content())
            try:
                os.mkdir(self.dest_dir.format(name))
            except OSError:
                pass

            self.get_photos(name, uri)
        return self.get_albums(id, offset, variant)

    def start(self):
        self.go_vk(self.grab_uid)
        if self.response.code == 200:
            st = self.response.unicode_body()
            try:
                return self.get_albums(re.search(r'\"\/photos-(\d+)\"', st).group(1), 0, self.GROUP)
            except AttributeError:
                return self.get_albums(re.search(r'\"\/photos(\d+)\"', st).group(1), 0, self.USER)
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

if __name__ == '__main__':
    #test()
    main()

# vi: ft=python:tw=0:ts=4

