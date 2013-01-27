#!/usr/bin/env python

import logging
import os
import urllib2

from django.core.files.temp import NamedTemporaryFile
from django.core.files.base import File

from activities.utils import TCXTrack

def create_preview(track):
    logging.debug("Creating preview image for track")
    if track:
        tcxtrack = TCXTrack(track)

        pos_list = tcxtrack.get_pos(90)
        if len(pos_list) > 1:
            gmap_coords = []
            for (lat, lon) in pos_list:
                gmap_coords.append("%s,%s" % (round(lat, 4), round(lon, 4)))
            gmap_path = "|".join(gmap_coords)

            url = "http://maps.google.com/maps/api/staticmap?size=480x480&path=color:0xff0000ff|"+gmap_path+"&sensor=true"
            logging.debug("Fetching file from %s" % url)
            logging.debug("Length of url is %s chars" % len(url))
            try:
                img_temp = NamedTemporaryFile(delete=True)
                img_temp.write(urllib2.urlopen(url).read())
                img_temp.flush()
                name=os.path.splitext(os.path.split(track.trackfile.name)[1])[0]
                logging.debug("Saving as %s.jpg" % name)

                track.preview_img.save("%s.jpg" % name, File(img_temp), save=True)
            except urllib2.URLError, exc:
                logging.error("Exception occured when creating preview image: %s" % exc)
        else:
            logging.debug("Track has no GPS position data, not creating preview image")
            # TODO: Maybe load fallback image as preview_image

