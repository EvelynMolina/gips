#!/usr/bin/env python
################################################################################
#    GIPS: Geospatial Image Processing System
#
#    Copyright (C) 2017 Applied Geosolutions
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see <http://www.gnu.org/licenses/>
################################################################################

from __future__ import print_function

import os
import shutil
import sys
import datetime
import shlex
import re
import subprocess
import json
import tempfile
import zipfile

import gippy
import gippy.algorithms

from gips.data.core import Repository, Asset, Data
from gips import utils

from gips.atmosphere import SIXS, MODTRAN


class sentinel2Repository(Repository):
    name = 'Sentinel-2'
    description = 'Data from the Sentinel 2 satellite(s) from the ESA'
    # when looking at the tiles shapefile, what's the key to fetch a feature's tile ID?
    _tile_attribute = 'Name'


class sentinel2Asset(Asset):
    Repository = sentinel2Repository

    _sensors = {
        'S2A': {
            'description': 'Sentinel-2, Satellite A',
            'bands': ['1', '2', '3', '4', '5', # specified by the driver
                      '6', '7', '8', '8a', '9',
                      '10', '11', '12'],
            'band_strings': ['01', '02', '03', '04', '05', # found in the granule filenames
                             '06', '07', '08', '8A', '09',
                             '10', '11', '12'],
            # for GIPS' & gippy's use, not inherent to driver
            'colors': ["COASTAL", "BLUE", "GREEN", "RED", "REDEDGE1",
                       "REDEDGE2", "REDEDGE3", "NIR", "REDEDGE4", "WV",
                       "CIRRUS", "SWIR1", "SWIR2"],
            'bandlocs': [0.443, 0.490, 0.560, 0.665, 0.705, # 'probably' center wavelength of band
                         0.740, 0.783, 0.842, 0.865, 0.945, # in micrometers
                         1.375, 1.610, 2.190],
            'bandwidths': [0.020, 0.065, 0.035, 0.030, 0.015, # 'probably' width of band, evenly
                           0.015, 0.020, 0.115, 0.020, 0.020, # split in the center by bandloc
                           0.030, 0.090, 0.180],
            # 'E': None  # S.B. Pulled from asset metadata file
            # 'K1': [0, 0, 0, 0, 0, 607.76, 0],  For conversion of LW bands to Kelvin
            # 'K2': [0, 0, 0, 0, 0, 1260.56, 0], For conversion of LW bands to Kelvin
            # 'tcap': _tcapcoef,

        },
    }
    _sensors['S2B'] = {'description': 'Sentinel-2, Satellite B'}

    # example url:
    # https://scihub.copernicus.eu/dhus/search?q=filename:S2?_MSIL1C_20170202T??????_N????_R???_T19TCH_*.SAFE

    _assets = {
        'L1C': {
            #                      sense datetime              tile
            #                     (YYYYMMDDTHHMMSS)            (MGRS)
            'pattern': 'S2?_MSIL1C_????????T??????_N????_R???_T?????_*.zip',
            'url': 'https://scihub.copernicus.eu/dhus/search?q=filename:',
            'startdate': datetime.date(2016, 12, 06),
            'latency': 3  # TODO actually seems to be 3,7,3,7..., but this value seems to be unused?
                          # only needed by Asset.end_date and Asset.available, but those are never called?
        },

    }

    _defaultresolution = (10, 10)  # 10m for optical
                                   # 20m for REDEDGE and SWIR bands
                                   # 60m for ATMOSPHERIC

    def __init__(self, filename):
        """Inspect a single file and set some metadata.

        Note that for now, only the shortened name format in use after Dec 6 2016 is supported:
        https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi/naming-convention
        """
        super(sentinel2Asset, self).__init__(filename)
        # TODO later do ZipFile().testzip() somewhere else & move this check there
        zipfile.ZipFile(filename) # sanity check; exception if file isn't a valid zip
        base_filename = os.path.basename(filename)
        # regex for verifying filename correctness & extracting metadata; note that for now, only
        # the shortened name format in use after Dec 6 2016 is supported:
        # https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi/naming-convention
        asset_name_pattern = ('^(?P<sensor>S2[AB])_MSIL1C_' # sensor
                              '(?P<year>\d{4})(?P<mon>\d\d)(?P<day>\d\d)T\d{6}' # year, month, day
                              '_N\d{4}_R\d\d\d_T(?P<tile>\d\d[A-Z]{3})_\d{8}T\d{6}.zip$') # tile
        match = re.match(asset_name_pattern, base_filename)
        if match is None:
            raise IOError("Asset file name is incorrect for Sentinel-2: '{}'".format(base_filename))
        self.asset = 'L1C'
        self.sensor = match.group('sensor')
        self.tile = match.group('tile')
        self.date = datetime.date(*[int(i) for i in match.group('year', 'mon', 'day')])

    @classmethod
    def fetch(cls, asset, tile, date):
        """Fetch the asset corresponding to the given asset type, tile, and date."""
        # set up fetch params
        year, month, day = date.timetuple()[:3]
        username = cls.Repository.get_setting('username')
        password = cls.Repository.get_setting('password')

        # search for the asset's URL with wget call (using a suprocess call to wget instead of a
        # more conventional call to a lib because available libs are perceived to be inferior).
        #                              year mon day                    tile
        url_search_string = 'S2?_MSIL1C_{}{:02}{:02}T??????_N????_R???_T{}_*.SAFE&format=json'
        search_url = cls._assets[asset]['url'] + url_search_string.format(year, month, day, tile)
        search_cmd = (
                'wget --no-verbose --no-check-certificate --user="{}" --password="{}" --timeout 30'
                ' --output-document=/dev/stdout "{}"').format(username, password, search_url)
        with utils.error_handler("Error performing asset search '({})'".format(search_url)):
            args = shlex.split(search_cmd)
            p = subprocess.Popen(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            (stdout_data, stderr_data) = p.communicate()
            if p.returncode != 0:
                verbose_out(stderr_data, stream=sys.stderr)
                raise IOError("Expected wget exit status 0, got {}".format(p.returncode))
            results = json.loads(stdout_data)['feed'] # always top-level key

            result_count = int(results['opensearch:totalResults'])
            if result_count == 0:
                return # nothing found, a normal occurence for eg date range queries
            if result_count > 1:
                raise IOError(
                        "Expected single result, but query returned {}.".format(result_count))

            entry = results['entry']
            # TODO entry['summary'] is good for printing out for user consumption
            link = entry['link'][0]
            if 'rel' in link: # sanity check - the right one doesn't have a 'rel' attrib
                raise IOError("Unexpected 'rel' attribute in search link", link)
            asset_url = link['href']
            output_file_name = entry['title'] + '.zip'

        # download the asset via the asset URL, putting it in a temp folder, then move to the stage
        # if the download is successful (this is necessary to avoid a race condition between
        # archive actions and fetch actions by concurrent processes)
        fetch_cmd_template = ('wget --no-check-certificate --user="{}" --password="{}" --timeout=30'
                              ' --no-verbose --output-document="{}" "{}"')
        if gippy.Options.Verbose() != 0:
            fetch_cmd_template += ' --show-progress --progress=dot:giga'
        utils.verbose_out("Fetching " + output_file_name)
        with utils.error_handler("Error performing asset download '({})'".format(asset_url)):
            tmp_dir_full_path = tempfile.mkdtemp(dir=cls.Repository.path('stage'))
            try:
                output_full_path = os.path.join(tmp_dir_full_path, output_file_name)
                fetch_cmd = fetch_cmd_template.format(
                        username, password, output_full_path, asset_url)
                args = shlex.split(fetch_cmd)
                p = subprocess.Popen(args)
                p.communicate()
                if p.returncode != 0:
                    raise IOError("Expected wget exit status 0, got {}".format(p.returncode))
                stage_full_path = os.path.join(cls.Repository.path('stage'), output_file_name)
                os.rename(output_full_path, stage_full_path) # on POSIX, if it works, it's atomic
            finally:
                shutil.rmtree(tmp_dir_full_path) # always remove the dir even if things break

    def updated(self, newasset):
        '''
        Compare the version for this to that of newasset.
        Return true if newasset version is greater.
        '''
        return (self.sensor == newasset.sensor and
                self.tile == newasset.tile and
                self.date == newasset.date and
                self.version < newasset.version)


class sentinel2Data(Data):
    name = 'Sentinel-2'
    version = '0.1.0'
    Asset = sentinel2Asset

    _productgroups = {
        'Index': ['ndvi'],
    }
    _products = {
        # placeholder product standing in for the real thing so fetch can work
        'ndvi': {
            'description': 'Normalized Difference Vegetation Index',
            'assets': ['L1C'],
        },
    }

    @classmethod
    def meta_dict(cls):
        meta = super(sentinel2Data, cls).meta_dict()
        meta['GIPS-sentinel2 Version'] = cls.version
        return meta


    def load_metadata(self):
        """Ingest metadata XML in Sentinel-2 SAFE asset files."""
        if hasattr(self, 'metadata'):
            return # nothing to do if metadata is already loaded

        # only one asset type supported for this driver so for now hardcoding is ok
        asset_type = 'L1C'
        datafiles = self.assets[asset_type].datafiles()

        # restrict filenames known to just the raster layers
        raster_fn_pat = '^.*/GRANULE/.*/IMG_DATA/.*_B\d[\dA].jp2$'
        fnl = [df for df in datafiles if re.match(raster_fn_pat, df)]
        # have to sort the list or else gippy will get confused about which band is which
        band_strings = sentinel2Asset._sensors[self.sensors[asset_type]]['band_strings']
        fnl.sort(key=lambda f: band_strings.index(f[-6:-4]))
        self.metadata = {'filenames': fnl}

    def read_raw(self):
        """Read in bands using original SAFE asset file (a .zip)."""
        start = datetime.datetime.now()
        self.load_metadata()

        # TODO support GDAL virtual filesystem later
        datafiles = self.assets['L1C'].extract(self.metadata['filenames'])
        #if settings().REPOS[self.Repository.name.lower()]['extract']:
        #    # Extract files to disk
        #    datafiles = self.assets['L1C'].extract(self.metadata['filenames'])
        #else:
        #    # Use zipfile directly using GDAL's virtual filesystem
        #    datafiles = [os.path.join('/vsizip/' + self.assets['L1C'].filename, f)
        #            for f in self.metadata['filenames']]

        image = gippy.GeoImage(datafiles)
        image.SetNoData(0) # inferred rather than taken from spec

        sensor = self.assets['L1C'].sensor
        # dict describing specification for all the bands in the asset
        data_spec = self.assets['L1C']._sensors[sensor]

        colors = self.assets['L1C']._sensors[sensor]['colors']
        filenames = self.metadata['filenames']

        assert len(filenames) == len(colors) # sanity check

        # go through all the files/bands in the image object and set values for each one
        for i, color in zip(range(1, len(colors) + 1), colors):
            image.SetBandName(color, i)

        utils.verbose_out('%s: read in %s' % (image.Basename(), datetime.datetime.now() - start), 2)
        return image


    def process(self, products=None, overwrite=False, **kwargs):
        """Produce data products and save them to files.

        If `products` is None, it processes all products.  If
        `overwrite` is True, it will overwrite existing products if they
        are found.  Products are saved to a well-known or else specified
        directory.
        """
        products = self.needed_products(products, overwrite)
        for val in products.requested.values():
            toa = (self._products[val[0]].get('toa', False) or 'toa' in val)
            if not toa:
		raise NotImplementedError('only toa products are supported for now')

        start = datetime.datetime.now()

        asset_type = 'L1C' # only one in the driver for now, conveniently

        # construct as much of the product filename as we can right now
        filename_prefix = self.basename + '_' + self.sensors[asset_type]

        # Read the assets
        with utils.error_handler('Error reading '
                                 + utils.basename(self.assets[asset_type].filename)):
            img = self.read_raw()

        for i, b in enumerate(img):
            print('band{bn} shape is {x}x{y}'.format(bn=i+1, x=b.XSize(), y=b.YSize()))

        md = self.meta_dict()

        sensor = self.sensors[asset_type]

        # Process Indices - right now just NDVI, so some of the loop/conditional structure is
        # technically not needed
        indices = products.groups()['Index']
        if len(indices) > 0:
            start = datetime.datetime.now()
            # fnames = mapping of product-to-output-filenames, minus filename extension (probably .tif)
            # reminder - indices' values are the keys, split by hyphen, eg {ndvi-toa': ['ndvi', 'toa']}
            fnames = {indices[key][0]: os.path.join(self.path, self.basename + '_' + key) for key in indices}
            prodout = gippy.algorithms.Indices(img, fnames, md)
            [self.AddFile(sensor, key, fname) for key, fname in zip(indices, prodout.values())]
            utils.verbose_out(' -> %s: processed %s in %s' % (
                    self.basename, indices.keys(), datetime.datetime.now() - start), 1)
        img = None # clue for the gc to reap img; probably needed due to C++/swig weirdness
        prodout = None # more gc hinting; may not be as necessary as img
        # cleanup directory here if necessary
