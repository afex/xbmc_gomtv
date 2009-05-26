import xbmc
import xbmcgui
import xbmcplugin

import os.path
import re
import urllib
from resources.lib.gomtv.scraper import CategoryScraper, VideoScraper

import xbmcgui
pDialog = xbmcgui.DialogProgress()
pDialog.create( "GOMTV" )

def download_hook( count, blocksize, totalsize ):
  percent = int( float( count * blocksize * 100) / totalsize )
  msg1 = "Downloading video..."
  msg2 = ""
  pDialog.update( percent, msg1, msg2 )
  if ( pDialog.iscanceled() ): raise
  
if ( __name__ == "__main__" ):
  if ( not sys.argv[ 2 ] ):
    cats = CategoryScraper().fetch()
    
    for id in cats:
      listitem = xbmcgui.ListItem(cats[id]['title'], cats[id]['description'])
      listitem.setInfo( "video", { "Title": cats[id]['title'], "Plot": cats[id]['description'] } )
      listitem.setThumbnailImage(cats[id]['image_url'])
      url = "%s?view_category=True&cat_id=%s" % (sys.argv[0], id)
      xbmcplugin.addDirectoryItem(handle=int( sys.argv[1] ), url=url, listitem=listitem, isFolder=True, totalItems=len(cats))
    
    xbmcplugin.endOfDirectory(handle=int( sys.argv[1] ), succeeded=True)
    
  elif (sys.argv[2].startswith("?view_category")):
    vs = VideoScraper()
    cat_id = re.search(r'cat_id=(.*)', sys.argv[2]).group(1)
    
    page_count = vs.fetch_page_count(cat_id)
    vids = {}
    for i in range(int(page_count)):
      msg1 = "Loading channel %s: Page %s" % (cat_id, str(i+1))
      msg2 = ""
      pDialog.update( ((i+1) / int(page_count)) * 100, msg1, msg2 )
      vids.update(vs.fetch_list(cat_id, i+1))
      
    vids = vs.combine_matches(vids)

    vs.cache_matches(cat_id, vids)
    
    for id in vids:
      listitem = xbmcgui.ListItem(vids[id]['title'], vids[id]['description'])
      listitem.setInfo( "video", { "Title": vids[id]['title'], "Plot": vids[id]['description'], "Date": vids[id]['date_string'] } )
      listitem.setProperty( "releasedate", vids[id]['posted_date'] )
      listitem.setThumbnailImage(vids[id]['image_url'])
      url = "%s?play_video=True&cat_id=%s&match_id=%s" % (sys.argv[0], cat_id, id)
      xbmcplugin.addDirectoryItem(handle=int( sys.argv[1] ), url=url, listitem=listitem, isFolder=False)
    
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_EPISODE)
    xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_TITLE)
    xbmcplugin.setContent(handle=int( sys.argv[1] ), content="movies")  
    xbmcplugin.endOfDirectory(handle=int( sys.argv[1] ), succeeded=True)
  
  elif (sys.argv[2].startswith("?play_video")):
    vs = VideoScraper()
    cat_id = re.search(r'cat_id=(.*)&match_id', sys.argv[2]).group(1)
    match_id = re.search(r'match_id=(.+)', sys.argv[2]).group(1)
    
    matches = vs.load_cached_matches(cat_id)
    vids = matches[match_id]['vids']
    
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    
    fetched_vids = {}
    for game_num in vids:
      vid = vs.fetch_video(cat_id, vids[game_num]['id'])
      if vid:
        vs.download_video(vid, download_hook)
        listitem = xbmcgui.ListItem(vid['title'])
        playlist.add(vid['local_vid_path'], listitem)
    
    pDialog.close()
    xbmc.Player().play(playlist)
  
sys.modules.clear()