# A Kodi Addon to play video hosted on the peertube service (http://joinpeertube.org/)
#
# This is just a Proof-Of-Concept atm but I hope I will be able to make it evolve to
# something worth using.
#
# TODO: - Delete downloaded files by default
#       - Allow people to choose if they want to keep their download after watching?
#       - Make sure we are seeding when downloading and watching
#       - When downloaded torrents are kept, do we want to seed them all the time,
#         or only when the addon is running, or only when kodi is playing one,...?
#       - Do sanity checks on received data
#       - Add a menu: 1) browse instance, 2) browse connected instances, 3) connect to ..., 4) search...

import time, sys
import urllib2, json
from urlparse import parse_qsl
import xbmc, xbmcgui, xbmcaddon, xbmcplugin, xbmcvfs
import AddonSignals

# Get the plugin url in plugin:// notation.
__url__ = sys.argv[0]
# Get the plugin handle as an integer number.
__handle__ = int(sys.argv[1])

class PeertubeAddon():
    """
    Main class of the addon
    """

    def __init__(self):
        """
        Initialisation of the PeertubeAddon class
        """

        xbmc.log('PeertubeAddon: Initialising', xbmc.LOGDEBUG)
        # Nothing to play at initialisation
        self.play = 0
        self.torrent_name = ''
        self.addon = xbmcaddon.Addon()
        
        return None

    def list_videos(self):
        """
        Create the list of playable videos in the Kodi interface.
        :param: None
        :return: None
        """

        # Get the user's preferred peertube instance
        inst = self.addon.getSetting('preferred_instance')

        # Get the list of videos published by the instance
        # TODO: Handle failures
        #       Make count configurable
        #       Set up pagination
        resp = urllib2.urlopen(inst + '/api/v1/videos?count=21')
        videos = json.load(resp)

        # Return when no videos are found
        if videos['total'] == 0:
            return

        # Create a list for our items.
        listing = []
        for video in videos['data']:

            # Create a list item with a text label
            list_item = xbmcgui.ListItem(label=video['name'])
        
            # Add thumbnail
            list_item.setArt({'thumb': inst + '/' + video['thumbnailPath']})

            # Set a fanart image for the list item.
            #list_item.setProperty('fanart_image', video['thumb'])

            # Compute media info from video's metadata
            info = {'title': video['name'],
                    'playcount': video['views'],
                    'plotoutline': video['description'],
                    'duration': video['duration']
                    }

            # Add a rating based on likes and dislikes
            if video['likes'] > 0 or video['dislikes'] > 0:
                info['rating'] = video['likes']/(video['likes'] + video['dislikes'])

            # Set additional info for the list item.
            list_item.setInfo('video', info) 

            # This is mandatory for playable items!
            list_item.setProperty('IsPlayable', 'true')

            # Find smallest file's torrentUrl
            # TODO: Get the best quality torrent given settings and/or available bandwidth
            #       See how they do that in the peerTube client's code 
            min_size = -1
            resp = urllib2.urlopen(inst + '/api/v1/videos/' + video['uuid'])
            metadata = json.load(resp)
            for f in metadata['files']:
              if f['size'] < min_size or min_size == -1:
                torrent_url = f['torrentUrl'] 

            # Add our item to the listing as a 3-element tuple.
            url = '{0}?action=play&url={1}'.format(__url__, torrent_url)
            listing.append((url, list_item, False))

        # Add our listing to Kodi.
        xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
        xbmcplugin.addSortMethod(__handle__, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
        xbmcplugin.endOfDirectory(__handle__)

    def play_video_continue(self, data):
        """
        Callback function to let the play_video function resume when the PeertubeDownloader
            has downloaded all the torrent's metadata
        :param data: dict
        :return: None
        """

        xbmc.log('PeertubeAddon: Received metadata_downloaded signal, will start playing media', xbmc.LOGDEBUG)
        self.play = 1    
        self.torrent_f = data['file']

        return

    def play_video(self, torrent_url):
        """
        Start the torrent's download and play it while being downloaded
        :param torrent_url: str
        :return: None
        """

        xbmc.log('PeertubeAddon: playing video ' + torrent_url, xbmc.LOGDEBUG)
        # Start a downloader thread
        AddonSignals.sendSignal('start_download', {'url': torrent_url})

        # Wait until the PeerTubeDownloader has downloaded all the torrent's metadata + a little bit more
        AddonSignals.registerSlot('plugin.video.peertube', 'metadata_downloaded', self.play_video_continue)
        while self.play == 0:
            xbmc.sleep(1000)
        xbmc.sleep(3000)

        # Pass the item to the Kodi player for actual playback.
        play_item = xbmcgui.ListItem(path=self.torrent_f)
        xbmcplugin.setResolvedUrl(__handle__, True, listitem=play_item)

    def router(self, paramstring):
        """
        Router function that calls other functions
        depending on the provided paramstring
        :param paramstring: dict
        :return: None
        """

        # Parse a URL-encoded paramstring to the dictionary of
        # {<parameter>: <value>} elements
        params = dict(parse_qsl(paramstring[1:]))

        # Check the parameters passed to the plugin
        if params:
            # Play a video from a provided URL.
            self.play_video(params['url'])
        else:
            # Display the list of videos when the plugin is called from Kodi UI without any parameters
            self.list_videos()

if __name__ == '__main__':

    # Initialise addon
    addon = PeertubeAddon()
    # Call the router function and pass the plugin call parameters to it.
    addon.router(sys.argv[2])
