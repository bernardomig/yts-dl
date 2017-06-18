#!/usr/bin/env python3

import os
import argparse
import requests
from bs4 import BeautifulSoup as soup
import inquirer

class Torrent:
    def __init__(self, quality, url):
        self.quality = quality
        self.url     = url

    def download(self):
        res = requests.get(self.url)
        if res.status_code == 200:
            return res.content
        else:
            raise Exception('Torrent was not downloaded.')

    def save(self, path):
        with open(path, 'wb') as f:
            f.write(self.download())

class Movie:

    def __init__(self, title, year, url=None):
        self.title = title
        self.year  = year
        self.url   = url
        self.torrents = []

    def __repr__(self):
        return "{} [{}]".format(self.title, self.year)

    def add_torrent(self, torrent):
        self.torrents.append(torrent)

    def filename(self):
        buf = '{}.{}'.format(self.title.strip().lower().replace(' ', '.'), self.year)
        buf = "".join(c for c in buf if c.isalnum() or c == '.')
        return buf

    def save_torrents(self, base_dir, quality=None):
        torrent_files = []
        if quality != 'all' and quality != None:
            torrents = [torrent for torrent in self.torrents if torrent.quality == quality]
        else:
            torrents = self.torrents

        for torrent in torrents:
            filename = "{}.{}.torrent".format(self.filename(), torrent.quality)
            full_path = os.path.join(base_dir, filename)
            torrent.save(full_path)
            torrent_files.append(full_path)
        return torrent_files

class Scrapper:

    def __init__(self, url):
        self.url = url

    def search(self, title, quality='all', genre='all', rating='0', sort='latest', n=0):
        url = "{}/browse-movies/{}/{}/{}/{}/{}".format(self.url, title, quality, genre, rating, sort)
        movies = []
        page = 1
        while True:
            page_str = '' if page == 1 else "?page={}".format(page)
            full_url = url + page_str
            html = soup(requests.get(full_url).content, 'html.parser')
            found_movies = html.find_all('div', class_='browse-movie-bottom')
            if len(found_movies) == 0:
                break
            for movie_html in found_movies:
                movie = Movie(
                    movie_html.find(class_='browse-movie-title').text,
                    movie_html.find(class_='browse-movie-year').text,
                    movie_html.find(class_='browse-movie-title')['href']
                    )
                for torrent in movie_html.find(class_='browse-movie-tags').find_all('a'):
                    movie.add_torrent(Torrent(
                        quality=torrent.text,
                        url=torrent['href']
                        ))
                movies.append(movie)
                if len(movies) == n and n > 0:
                    return movies

            page += 1
        return movies

if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        prog='yts-dl',
        description='An yts.ag client for search and download torrents'
        )

    parser.add_argument(
        'movie',
        nargs='+',
        type=str,
        help='title of the movie(s) to search.'
        )
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='.',
        help='directory destination of the torrent files'
        )
    parser.add_argument(
        '-s', '--sort',
        choices=['latest', 'oldest', 'seeds', 'peers', 'year', 'rating', 'likes', 'alphabetical', 'downloads'],
        help='sort the search'
    )
    parser.add_argument(
        '-n', '--number',
        type=int,
        default=20,
        help='number of movies to download'
    )
    parser.add_argument(
        '-r', '--rating',
        type=int,
        default=0,
        help='minimum rating (IMdb) to download a torrent'
    )
    parser.add_argument(
        '-p', '--proxy',
        type=str,
        default='https://yts.ag',
        help='url of the yts.ag proxy'
    )
    parser.add_argument(
        '-q', '--quality',
        choices=['720p', '1080p', '3D'],
        default='all',
        help='quality of the movie to download'
    )
    parser.add_argument(
        '-g', '--genre',
        default='all',
        choices=['action', 'adventure', 'animation', 'biography', 'comedy', 'crime',
                 'documentary', 'drama', 'family', 'fantasy', 'film-noir', 'game-show',
                 'history', 'horror', 'music', 'musical', 'mystery', 'mystery', 'news',
                 'reality-tv', 'romance', 'sci-fi', 'sport', 'talk-show', 'thriller',
                 'war', 'western'],
        help='genre of the movie to download'
    )
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='download without asking'
    )
    parser.add_argument(
        '--run-torrents',
        action='store_true',
        help='run the torrents using the default program'
    )

    args = parser.parse_args()

    scrapper = Scrapper(args.proxy)

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    search_results = []

    for movie_search in args.movie:
        movies = scrapper.search(movie_search,
            quality=args.quality,
            genre=args.genre,
            rating=args.rating,
            sort=args.sort,
            n=args.number)
        search_results += movies

    torrent_files = []

    if args.yes:
        for movie in search_results:
            torrent_files += movie.save_torrents(args.output_dir, args.quality)
    else:
        for idx, movie in enumerate(search_results):
            print("[{:3d}]\t{}".format(idx+1, movie))
        selection = [int(i) for i in input('Select movies to download: ').split()]
        for idx in selection:
            torrent_files += search_results[idx-1].save_torrents(args.output_dir, args.quality)

    if args.run_torrents:
        from sys import platform
        from subprocess import call

        if platform in ['linux', 'linux2', 'darwin']:
            for file in torrent_files:
                call(['xdg-open', file])
        elif platform == 'win32':
            pass
