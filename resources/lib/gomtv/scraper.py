import urllib, urllib2
import re
import datetime
import os, os.path
import md5
import pickle

import xbmc
from resources.lib.external.BeautifulSoup import BeautifulSoup

class CategoryScraper:
  category_url = 'http://www.gomtv.net/channel/'
  
  def fetch(self):
    cats = {}
    
    response = urllib2.urlopen(self.category_url)
    contents = response.read()
    page = BeautifulSoup(contents)
    
    channels = page.findAll('div', {'id': 'Channels1'})
    if channels:
      for channel in channels:        
        shows = channel.findAll('dl')
        for show in shows:
          id = re.sub(r'http://www\.gomtv\.net/(.*)/', r'\1', show.dt.a['href'])
          image_url = show.find('dd', 'img').img['src']
          if image_url.startswith('/'):
            image_url = 'http://www.gomtv.net' + image_url
          description = show.find('dd', 'txt').renderContents()
          cats[id] = {'id': id, 'title': show.dt.a.string, 'description': description, 'image_url': image_url }

    return cats
    
class VideoScraper:
  base_data_path = os.path.join( xbmc.translatePath( "P:\\plugin_data" ), "video", 'GOMTV' )
  video_list_url = 'http://www.gomtv.net/%s/vod/?page=%s'
  video_url = 'http://www.gomtv.net/%s/vod/%s'
  
  def __init__(self):
    try:
        self.date_format = xbmc.getRegion( "datelong" ).replace( "DDDD,", "" ).replace( "MMMM", "%B" ).replace( "D", "%d" ).replace( "YYYY", "%Y" ).strip()
    except:
        self.date_format = "%B %d, %Y"
        
  def fetch_page_count(self, cat_id):
    count = 0
    
    response = urllib2.urlopen(self.video_list_url % (cat_id, 1))
    contents = response.read()
    page = BeautifulSoup(contents)
    
    link_table = page.find('table', {'id': 'bbsnum'})
    count = re.search(r"<a href=\"\./\?page=(\d+)&[^>]*>Last >></a>", link_table.renderContents()).group(1)
    
    return count    
    
  def fetch_list(self, cat_id, page = 1):
    vids = {}
    
    response = urllib2.urlopen(self.video_list_url % (cat_id, page))
    contents = response.read()
    page = BeautifulSoup(contents)
    
    matches = page.findAll('td', 'listOff')
    if matches:
      for match in matches:
        primary_link = match.find('a', 'vodlink')
        id = primary_link['href'].replace('./', '')
        if id.startswith('javascript'):
          continue
        re_match = re.search(r'Posted: (\d+) (\d+)/(\d+)<', match.parent.find('td', 'sect').renderContents())
        year = re_match.group(1)
        month = re_match.group(2)
        day = re_match.group(3)
        date_string = "%s-%s-%s" % (day, month, year)
        posted_date = datetime.date(int(year), int(month), int(day)).strftime(self.date_format)
        image_url = 'http://www.gomtv.net' + match.find('img')['src']
        local_image_path = os.path.join(self.base_data_path, cat_id, str(id) + '.tbn')
        if not os.path.exists(os.path.join(self.base_data_path, cat_id)):
          os.makedirs(os.path.join(self.base_data_path, cat_id))
        if not os.path.isfile(local_image_path):
          urllib.urlretrieve(image_url, local_image_path)
        vids[id] = {'id': int(id),
                    'date_string': date_string,
                    'posted_date': posted_date,
                    'year': year,
                    'title': str(primary_link.string),
                    'description': str(match.find('div', 'vodinfo').renderContents()), 
                    'image_url': local_image_path}
    return vids
    
  def combine_matches(self, videos):
    combined = {}

    for id in videos:
      # Effort vs Mind- Game 3 [Ro.32 Group 11]
      # Violet vs Practice - Game3 [Ro.32 Group 10] 
      re_match = re.match(r'(.*) +(vs) +([^ \[-]*)[ -]+Game ?(\d+) +\[(.*)\]', videos[id]['title'], re.I)
      if re_match:
        match_name = re_match.group(1) + ' vs ' + re_match.group(3) + ' [' + re_match.group(5) + ']'
        match_id = md5.new(match_name).hexdigest()
        game_num = int(re_match.group(4))
      else:
        match_id = md5.new(videos[id]['title']).hexdigest()
        match_name = videos[id]['title']
        game_num = 1
        
      if match_name in combined:
        combined[match_name]['vids'][game_num] = videos[id]
      else:
        combined[match_name] = {'title': match_name, 
                                'description': videos[id]['description'], 
                                'year': videos[id]['year'], 
                                'posted_date': videos[id]['posted_date'], 
                                'date_string': videos[id]['date_string'],
                                'image_url': videos[id]['image_url'],
                                'vids': { game_num: videos[id] }}
        
    return combined
      
  def cache_matches(self, cat_id, matches):
    f = open(os.path.join(self.base_data_path, cat_id, 'cache.pickle'), 'w')
    try:
      pickle.dump(matches, f)
    finally:
      f.close()
      
    return True
      
  def load_cached_matches(self, cat_id):
    f = open(os.path.join(self.base_data_path, cat_id, 'cache.pickle'))
    try:
      obj = pickle.load(f)
    finally:
      f.close()
    
    return obj
        
  def fetch_video(self, cat_id, vid_id):
    vid = None
    
    response = urllib2.urlopen(self.video_url % (cat_id, vid_id))
    contents = response.read()
    page = BeautifulSoup(contents)
    
    re_match = re.search(r'\.swf\?link=(\d+)', page.renderContents())
    if re_match:
      vid = {}
      file_id = re_match.group(1)
    
      vid['title'] = page.find('div', {'id': 'bbsDetail'}).h3.string
      vid['file_url'] = 'http://flvdn.gomtv.net/viewer/%s.flv' % file_id
      if not os.path.exists(os.path.join(self.base_data_path, cat_id)):
        os.makedirs(os.path.join(self.base_data_path, cat_id))
      vid['local_vid_path'] = os.path.join(self.base_data_path, cat_id, str(vid_id) + '.flv')
    
    return vid
    
  def download_video(self, video, callback_func):
    try:
      if not os.path.exists(video['local_vid_path']):
        if callback_func:
          urllib.urlretrieve(video['file_url'], video['local_vid_path'], callback_func)
        else:
          urllib.urlretrieve(video['file_url'], video['local_vid_path'])
    except Exception, e:
      urllib.urlcleanup()
      remove_tries = 3
      while remove_tries and os.path.isfile(video['local_vid_path']):
        try:
          os.remove(video['local_vid_path'])
        except:
          remove_tries -= 1
          xbmc.sleep( 1000 )
      raise e
      
    return True