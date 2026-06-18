# VERSION: 1.4
# AUTHORS: BurningMop (burning.mop@yandex.com)

# LICENSING INFORMATION
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import re
from html.parser import HTMLParser
import time
import threading
from helpers import download_file, retrieve_url
from novaprinter import prettyPrinter

class xxxclubto(object):
    url = 'https://xxxclub.to'
    headers = {
        'Referer': url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    name = 'XXXClub'
    supported_categories = {
        'all': 'All',
        'pictures': '5',
    }

    container_regex = r'<div.*?class=".*?browsetableinside.*?".*?>(?s:.)*?<\/div>'
    pagination_regex = r'<div.*?class=".*?browsepagination.*?".*?>(?s:.)*?<\/div>'
    pagination_next_regex = r'<a.*?title="Next Page".*?>(?s:.)*?<\/a>'
    pagination_last_page = r'<a.*?class=".*?active.*?".*?>.*?</a>'
    items_regex = r'<li.*?>(?s:.)*?<\/li>'

    has_results = True
    has_next_page = True
    last_page = 100

    class MyHtmlParser(HTMLParser):

        def error(self, message):
            pass

        UL, LI, SPAN, A = ('ul', 'li', 'span', 'a')

        def __init__(self, url, headers):
            HTMLParser.__init__(self)
            self.url = url
            self.headers = headers
            self.headers['Referer'] = url
            self.row = {}
            self.column = 0
            self.foundResults = False
            self.foundTable = False
            self.insideRow = False
            self.insideCell = False
            self.insideNameLink = False
            self.foundTableHeading = False
            self.foundRowCatlabe = False
            self.magnet_regex = r'href="(magnet:[\?\S]+)"'

        def handle_starttag(self, tag, attrs):
            params = dict(attrs)
            if 'browsetableinside' in params.get('class', ''):
                self.foundResults = True
                return
            if self.foundResults and tag == self.UL:
                self.foundTable = True
                return
            if self.foundTable and tag == self.LI:
                self.insideRow = True
                return
            if self.insideRow and self.foundTableHeading and tag == self.SPAN:
                classList = params.get('class', '')
                if 'catlabe' in classList:
                    self.foundRowCatlabe = True
                self.insideCell = True
                self.column += 1
                return
            if self.insideRow and self.foundTableHeading and self.column == 1 and tag == self.A:
                self.insideNameLink = True
                href = params.get('href', '')
                link = f'{self.url}{href}'
                self.row['desc_link'] = link
                
                try:
                    torrent_page = retrieve_url(link, self.headers)
                    matches = re.findall(self.magnet_regex, torrent_page)
                    if matches:
                        self.row['link'] = matches[0]
                    else:
                        self.row['link'] = link
                except Exception:
                    self.row['link'] = link
                return

        def handle_data(self, data):
            if self.insideCell and self.foundRowCatlabe:
                data = data.strip()
                if not data:
                    return
                if self.column == 1 and self.insideNameLink:
                    self.row['name'] = data
                elif self.column == 3:
                    self.row['size'] = data.replace(',', '')
                elif self.column == 4:
                    self.row['seeds'] = data
                elif self.column == 5:
                    self.row['leech'] = data
                return

        def handle_endtag(self, tag):
            if self.insideCell and self.insideNameLink and tag == self.A:
                self.insideNameLink = False
            if self.insideCell and tag == self.SPAN:
                self.insideCell = False
            if self.insideRow and tag == self.LI:
                if not self.foundTableHeading:
                    self.foundTableHeading = True
                else:
                    if self.row.get('name'):
                        self.row['engine_url'] = self.url
                        prettyPrinter(self.row)
                self.insideRow = False
                self.foundRowCatlabe = False
                self.column = 0
                self.row = {}
                return

        def download_torrent(self, info):
            print(download_file(info))

        def get_page_url(self, what, category, page):
            return f'{self.url}/torrents/search/{category}/{what}?page={page}&sort=seeders&order=asc'

        def get_results(self, html):
            container_matches = re.finditer(self.container_regex, html, re.MULTILINE)
            container = [x.group() for x in container_matches]

            if len(container) > 0:
                container_html = container[0]
                items_matches = re.finditer(self.items_regex, container_html, re.MULTILINE)
                items = [x.group() for x in items_matches]
                self.has_results = len(items) > 1
            else:
                self.has_results = False

        def get_next_page(self, html):
            next_page_matches = re.finditer(self.pagination_next_regex, html, re.MULTILINE)
            next_page = [x.group() for x in next_page_matches]
            self.has_next_page = len(next_page) > 0
