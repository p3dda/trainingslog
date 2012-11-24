#!/usr/bin/python
"""Simple converter from TCX file to GPX format

Usage:   python tcx2gpx.py   foo.tcx  > foo.gpx

Streaming implementation works for large files.


Open Source: MIT Licencse.
This is or was <http://www.w3.org/2009/09/geo/tcx2gpx.py>
Author: http://www.w3.org/People/Berners-Lee/card#i
Written: 2009-10-30
Last change: $Date: 2009/10/28 13:44:33 $
"""
import urllib
from xml import sax
from xml.sax import saxutils
import logging
import sys, os


TCX_NS="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"

class MyHandler(sax.handler.ContentHandler):
	def __init__(self, w):
		self.time = ""
		self.lat = ""
		self.lon = ""
		self.alt = ""
		self.content = ""
		self.w = w
		self.min_lat = 1000.0
		self.max_lat = 0
		self.min_lon = 1000.0
		self.max_lon = 0

	def startDocument(self):
		self.w("""<gpx xmlns="http://www.topografix.com/GPX/1/1"
	creator="http://www.w3.org/2009/09/geo/tcx2gpx.py"
	version="1.1"
	xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
	xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
""")

	def endDocument(self):
		self.w(' <bounds minlat="%s" minlon="%s" maxlat="%s" maxlon="%s"/>\n' % (self.min_lat, self.min_lon, self.max_lat, self.max_lon))
		self.w('</gpx>\n')

	def startElement(self, name, attrs):

		self.content = ""
		if name == 'Track':
			self.w(' <trk>\n  <trkseg>\n')




	def characters(self, content):
		self.content = self.content + saxutils.escape(content)

#    def endElementNS(fname, qname, attrs):
#        (ns, name) = fname

	def endElement(self, name):
		if name == 'Track':
			self.w('  </trkseg>\n </trk>\n')
		elif name == 'Trackpoint':
			try:
				if float(self.lat) < self.min_lat:
					self.min_lat = float(self.lat)
				if float(self.lat) > self.max_lat:
					self.max_lat = float(self.lat)
				if float(self.lon) < self.min_lon:
					self.min_lon = float(self.lon)
				if float(self.lon) > self.max_lon:
					self.max_lon = float(self.lon)
			except ValueError, e:
				pass
			else:
				if (self.lon and self.lat):
					self.w('   <trkpt lat="%s" lon="%s">\n' % (self.lat, self.lon))
					if (self.alt): 
						self.w('    <ele>%s</ele>\n' % self.alt)
					if (self.time): 
						self.w('    <time>%s</time>\n' % self.time)
					self.w('   </trkpt>\n')
					sys.stdout.flush()
		elif name == 'LatitudeDegrees':
			self.lat = self.content
		elif name == 'LongitudeDegrees':
			self.lon = self.content
		elif name == 'AltitudeMeters':
			self.alt = self.content
		elif name == 'Time':
			self.time = self.content

def convert(tcxtrack):
	logging.debug("convert called with track %s" % tcxtrack)
	try:
		with open(tcxtrack.trackfile.path+".gpx", 'w') as f:
			logging.debug("Opened gpx file %s for write" % tcxtrack.trackfile.path+".gpx")
			w = f.write
			handler = MyHandler(w)
			sax.parse(tcxtrack.trackfile.path, handler)
	except Exception, msg:
		logging.debug("Exception occured in convert: %s" % msg)
