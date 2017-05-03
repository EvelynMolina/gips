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

import math
import os
import shutil
import sys
import datetime
import shlex
import re
import glob
import subprocess
import json
import tempfile
import zipfile
from xml.etree import ElementTree, cElementTree

import numpy

import gippy
import gippy.algorithms

from gips.data.core import Repository, Asset, Data
from gips import utils
from gips import atmosphere

"""Steps for adding a product to this driver:

* add the product to the _products dict
* make a $prod_geoimage() method to generate the GeoImage; follow pattern of others.
* add a stanza to the conditional below where $prod_geoimage is called.
* add the product to the dependency dict above.
* if atmo correction is in use:
    * save its metadata (see 'ref' for a pattern)
    * add the product to the conditional for metadata in the file-saving block
* update system tests
"""


class sentinel2Repository(Repository):
    name = 'Sentinel2'
    description = 'Data from the Sentinel 2 satellite(s) from the ESA'
    # when looking at the tiles shapefile, what's the key to fetch a feature's tile ID?
    _tile_attribute = 'Name'


class sentinel2Asset(Asset):
    Repository = sentinel2Repository

    _sensors = {
        'S2A': {
            'description': 'Sentinel-2, Satellite A',
            # Note all these lists are aligned with eachother, so that GREEN is band 3, and has
            # bandwidth 0.035.
            # found in the granule filenames
            'band-strings':
                ['01', '02', '03', '04', '05', '06',
                 '07', '08', '8A', '09', '10', '11', '12'],
            # for GIPS' & gippy's use, not inherent to driver
            'colors':
                ["COASTAL",  "BLUE", "GREEN",    "RED", "REDEDGE1", "REDEDGE2",
                 "REDEDGE3", "NIR",  "REDEDGE4", "WV",  "CIRRUS",   "SWIR1",    "SWIR2"],
            # center wavelength of band in micrometers, CF:
            # https://earth.esa.int/web/sentinel/user-guides/sentinel-2-msi/resolutions/radiometric
            'bandlocs':
                [0.443, 0.490, 0.560, 0.665, 0.705, 0.740,
                 0.783, 0.842, 0.865, 0.945, 1.375, 1.610, 2.190],
            # width of band, evenly split in the center by bandloc:
            # https://earth.esa.int/web/sentinel/user-guides/sentinel-2-msi/resolutions/radiometric
            'bandwidths':
                [0.020, 0.065, 0.035, 0.030, 0.015, 0.015,
                 0.020, 0.115, 0.020, 0.020, 0.030, 0.090, 0.180],
            'bandbounds':
                # low and high boundaries of each band; formatted this way to match other lists
                [(0.433, 0.453), (0.4575, 0.5225), (0.5425, 0.5775), (0.65, 0.68),
                    (0.6975, 0.7125), (0.7325, 0.7475),
                 (0.773, 0.793), (0.7845, 0.8995), (0.855, 0.875), (0.935, 0.955), (1.36, 1.39),
                    (1.565, 1.655), (2.1, 2.28)],
            # in meters per https://sentinel.esa.int/web/sentinel/user-guides/sentinel-2-msi/resolutions/spatial
            'spatial-resolutions':
                [60, 10, 10, 10, 20, 20,
                 20, 10, 20, 60, 60, 20, 20],
            # 'E': None  # S.B. Pulled from asset metadata file
            # 'tcap': _tcapcoef,

            # colors needed for computing indices products such as NDVI
            # color names are ['BLUE', 'GREEN', 'RED', 'NIR', 'SWIR1', 'SWIR2']
            'indices-bands': ['02', '03', '04', '08', '11', '12'],
            # similar to landsat's "visbands"
            'indices-colors': ['BLUE', 'GREEN', 'RED', 'NIR', 'SWIR1', 'SWIR2'],
            # landsat version: ['COASTAL', 'BLUE', 'GREEN', 'RED', 'NIR', 'SWIR1', 'SWIR2', 'CIRRUS'],
        },
    }
    _sensors['S2B'] = {'description': 'Sentinel-2, Satellite B'}

    _assets = {
        'L1C': {
            # 'pattern' is used for searching the repository of locally-managed assets; this pattern
            # is used for both original and shortened post-2016-12-07 assets.
            # TODO test this line after assets are archived (ie during Asset.discover)
            'pattern': '*S2?_*MSIL1C_*????????T??????_*R???_*.zip',
            # TODO find real start date for S2 data:
            # https://scihub.copernicus.eu/dhus/search?q=filename:S2?*&orderby=ingestiondate%20asc
            # (change to orderby=ingestiondate%20desc if needed)
            'startdate': datetime.date(2015, 1, 1), # used to prevent impossible searches
            'latency': 3, # actually seems to be 3,7,3,7..., but this value seems to be unused;
                          # only needed by Asset.end_date and Asset.available, but those are never called?
        },

    }

    _2016_12_07 = datetime.datetime(2016, 12, 7, 0, 0) # first day of new-style assets, UTC

    # regexes for verifying filename correctness & extracting metadata; convention:
    # https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi/naming-convention
    _asset_styles = {
        'original': {
            'name-re': ( # pattern for the asset file name
                # example, note that leading tile code is spliced in by Asset.fetch:
                # 19TCH_S2A_OPER_PRD_MSIL1C_PDMC_20170221T213809_R050_V20151123T091302_20151123T091302.zip
                '^(?P<tile>\d\d[A-Z]{3})_(?P<sensor>S2[AB])_OPER_PRD_MSIL1C_....' # tile & sensor
                '_\d{8}T\d{6}' # processing date (don't care)
                '_R(?P<rel_orbit>\d\d\d)' # relative orbit, not sure if want
                # observation datetime:
                '_V(?P<year>\d{4})(?P<mon>\d\d)(?P<day>\d\d)' # year, month, day
                'T(?P<hour>\d\d)(?P<min>\d\d)(?P<sec>\d\d)' # hour, minute, second
                '_\d{8}T\d{6}.zip'), # repeated observation datetime; probably don't care
            # raster file pattern
            'raster-re': r'^.*/GRANULE/.*/IMG_DATA/.*_T{tileid}_B\d[\dA].jp2$',
            # TODO
            ## internal metadata file patterns
            #'datastrip-md-re': '^.*/DATASTRIP/.*/MTD_DS.xml$',
            #'tile-md-re': '^.*/GRANULE/.*/MTD_TL.xml$',
            ## Two files with asset-global metadata, this is one of them:
            ## for INSPIRE.xml see http://inspire.ec.europa.eu/XML-Schemas/Data-Specifications/2892
            #'inspire-md-re': '^.*/INSPIRE.xml$',
        },
        _2016_12_07: {
            'name-re': ( # pattern for the asset file name
                '^(?P<sensor>S2[AB])_MSIL1C_' # sensor
                '(?P<year>\d{4})(?P<mon>\d\d)(?P<day>\d\d)' # year, month, day
                'T(?P<hour>\d\d)(?P<min>\d\d)(?P<sec>\d\d)' # hour, minute, second
                '_N\d{4}_R\d\d\d_T(?P<tile>\d\d[A-Z]{3})_\d{8}T\d{6}.zip$'), # tile
            # raster file pattern
            'raster-re': '^.*/GRANULE/.*/IMG_DATA/.*_B\d[\dA].jp2$',
            # internal metadata file patterns
            'datastrip-md-re': '^.*/DATASTRIP/.*/MTD_DS.xml$',
            'tile-md-re': '^.*/GRANULE/.*/MTD_TL.xml$',
            # Two files with asset-global metadata, this is one of them:
            # for INSPIRE.xml see http://inspire.ec.europa.eu/XML-Schemas/Data-Specifications/2892
            'inspire-md-re': '^.*/INSPIRE.xml$',
        },
    }

    # default resultant resolution for resampling during to Data().copy()
    _defaultresolution = (10, 10)

    def __init__(self, filename):
        """Inspect a single file and set some metadata.

        Both shortened and original longer file name & content structure are supported:
        https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi/naming-convention
        """
        super(sentinel2Asset, self).__init__(filename)
        zipfile.ZipFile(filename) # sanity check; exception if file isn't a valid zip
        base_filename = os.path.basename(filename)

        for style, style_dict in self._asset_styles.items():
            match = re.match(style_dict['name-re'], base_filename)
            if match is not None:
                break
        if match is None:
            raise IOError("Asset file name is incorrect for Sentinel-2: '{}'".format(base_filename))
        self.style = style
        self.style_res = self._asset_styles[style]
        self.asset = 'L1C' # only supported asset type
        self.sensor = match.group('sensor')
        self.tile = match.group('tile')
        self.date = datetime.date(*[int(i) for i in match.group('year', 'mon', 'day')])
        self.time = datetime.time(*[int(i) for i in match.group('hour', 'min', 'sec')])


    @classmethod
    def fetch(cls, asset, tile, date):
        """Fetch the asset corresponding to the given asset type, tile, and date."""
        # set up fetch params
        year, month, day = date.timetuple()[:3]
        username = cls.Repository.get_setting('username')
        password = cls.Repository.get_setting('password')

        style = 'original' if date < cls._2016_12_07 else cls._2016_12_07

        # TODO when issue #131 comes around, this is the beginning of the 'query' step
        # search step:  locate the asset corresponding to (asset, tile, date)
        url_head = 'https://scihub.copernicus.eu/dhus/search?q='
        url_tail = '&format=json'
        if style == 'original':
            # compute the center coordinate of the tile
            tiles_shp_fn = cls.Repository.get_setting('tiles')
            key = cls.Repository._tile_attribute
            vector = utils.open_vector(tiles_shp_fn, key) # type is gippy GeoFeature
            feature = vector[tile] # type is gippy GeoFeature
            extent = feature.Extent()
            lon = (extent.x0() + extent.x1())/2
            lat = (extent.y0() + extent.y1())/2
            #                                                  year mon  day
            url_search_string = ('filename:S2?_OPER_PRD_MSIL1C_*_{}{:02}{:02}T??????.SAFE'
                                 '%20AND%20footprint:%22Intersects({},%20{})%22') # <-- lat/lon
            search_url = url_head + url_search_string.format(year, month, day, lat, lon) + url_tail
        else:
            #                                      year mon  day                    tile
            url_search_string = 'filename:S2?_MSIL1C_{}{:02}{:02}T??????_N????_R???_T{}_*.SAFE'
            search_url = url_head + url_search_string.format(year, month, day, tile) + url_tail

        # search for the asset's URL with wget call (using a suprocess call to wget instead of a
        # more conventional call to a lib because available libs are perceived to be inferior).
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
            link = entry['link'][0]
            if 'rel' in link: # sanity check - the right one doesn't have a 'rel' attrib
                raise IOError("Unexpected 'rel' attribute in search link", link)
            asset_url = link['href']
            output_file_name = entry['title'] + '.zip'

        # old-style assets cover many tiles, so there may be duplication of effort; avoid that by
        # aborting if the stage already contains content for the desired asset/tile/date:
        ofn_glob = (tile.upper() + '_'
                    + re.sub(r'_\w{4}_\d{8}T\d{6}_', r'_????_????????T??????_', output_file_name, 1))
        stage_glob = os.path.join(cls.Repository.path('stage'), ofn_glob)
        if len(glob.glob(stage_glob)) > 0:
            utils.verbose_out('Asset `{}` needed but already in stage/, skipping.'.format(
                    output_file_name))
            return

        # TODO when issue #131 comes around, this is the beginning of the 'download' step
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
                cls.stage_asset(style, output_full_path, output_file_name)
            finally:
                shutil.rmtree(tmp_dir_full_path) # always remove the dir even if things break


    @classmethod
    def stage_asset(cls, style, asset_full_path, asset_base_name):
        """Copy the given asset to the stage.

        If the file is an old-style asset, it's exploded into many names,
        one per tile, so that the archivation process will behave properly.
        """
        stage_path = cls.Repository.path('stage')
        if style == 'original':
            # copy enough links into stage to do the thing successfully
            # the way to do this is by extracting the tile list from the asset
            tile_list = cls.tile_list(asset_full_path)
            for tile in tile_list:
                stage_fp = os.path.join(stage_path, tile + '_' + asset_base_name)
                os.link(asset_full_path, stage_fp)
        else:
            stage_full_path = os.path.join(stage_path, asset_base_name)
            os.rename(asset_full_path, stage_full_path) # on POSIX, if it works, it's atomic


    @classmethod
    def tile_list(cls, file_name):
        """Extract a list of tiles from the given old-style asset."""
        # "the only XML file one directory down from DATASTRIP/"
        file_pattern = '^.*/DATASTRIP/[^/]+/[^/]+\.xml$'
        subtree_tag = 'Tile_List'
        with zipfile.ZipFile(file_name) as asset_zf:
            metadata_fn = next(fn for fn in asset_zf.namelist() if re.match(file_pattern, fn))
            with asset_zf.open(metadata_fn) as metadata_zf:
                tree = cElementTree.parse(metadata_zf)
                tl_elem = next(tree.iter(subtree_tag))
                tiles_tags = tl_elem.findall('Tile')
                # from this:  S2A_OPER_MSI_L1C_TL_EPA__20170221T200353_A002192_T35UNQ_N02.04
                # want this:  35UNQ
                return [tt.attrib['tileId'].split('_')[-2][1:] for tt in tiles_tags]


    def updated(self, newasset):
        '''
        Compare the version for this to that of newasset.
        Return true if newasset version is greater.
        '''
        return (self.sensor == newasset.sensor and
                self.tile == newasset.tile and
                self.date == newasset.date and
                self.version < newasset.version)


    def xml_subtree(self, md_file_type, subtree_tag):
        """Loads XML, then returns the given Element from it.

        File to read is specified by type eg 'tile' or 'datastrip'.  The first
        matching tag in the XML tree is returned.  The metadata file is located
        in self.style_res eg 'tile' results in 'tile-md-re' being used.
        """
        file_pattern = self.style_res[md_file_type + '-md-re']
        # python idiom for "first item in list that satisfies a condition"
        metadata_fn = next(fn for fn in self.datafiles() if re.match(file_pattern, fn))
        with zipfile.ZipFile(self.filename) as asset_zf:
            with asset_zf.open(metadata_fn) as metadata_zf:
                tree = ElementTree.parse(metadata_zf)
                return next(tree.iter(subtree_tag))


    def solar_irradiances(self):
        """Loads solar irradiances from asset metadata and returns them.

        The order of the list matches the band list above.  Irradiance
        values are in watts/(m^2 * micrometers).
        """
        sil_elem = self.xml_subtree('datastrip', 'Solar_Irradiance_List')
        values_tags = sil_elem.findall('SOLAR_IRRADIANCE')
        # sanity check that the bands are in the right order
        assert range(13) == [int(vt.attrib['bandId']) for vt in values_tags]
        return [float(vt.text) for vt in values_tags]


    def mean_viewing_angle(self, angle='both'):
        """Loads & returns mean viewing angle:  (zenith, azimuth).

        Queries and returns asset metadata for these values.  Return
        value is in degrees.
        """
        if angle != 'both':
            raise NotImplementedError('getting zenith or azimuth separately is not supported')
        mvial_elem = self.xml_subtree('tile', 'Mean_Viewing_Incidence_Angle_List')
        # should only be one list, with 13 elems, each with 2 angles, a zen and an az
        angles = mvial_elem.findall('Mean_Viewing_Incidence_Angle')
        mean_zen = numpy.mean([float(e.find('ZENITH_ANGLE' ).text) for e in angles])
        mean_az  = numpy.mean([float(e.find('AZIMUTH_ANGLE').text) for e in angles])
        return (mean_zen, mean_az)


    def mean_solar_angle(self, angle='both'):
        """Loads & returns solar zenith and/or azimuth angle.

        Queries and returns asset metadata for these values.  Set angle
        to 'zenith' or 'azimuth' to get single values, or 'both' to get
        (zenith, azimuth).  Return value is in degrees.
        """
        assert angle in ('both', 'zenith', 'azimuth') # sanity check
        msa_elem = self.xml_subtree('tile', 'Mean_Sun_Angle')
        get_angle = lambda tag: float(msa_elem.find(tag).text)
        if angle == 'both':
            return (get_angle('ZENITH_ANGLE'), get_angle('AZIMUTH_ANGLE'))
        if angle == 'zenith':
            return get_angle('ZENITH_ANGLE')
        if angle == 'azimuth':
            return get_angle('AZIMUTH_ANGLE')


    def tile_lat_lon(self):
        """Loads & returns boundaries for this asset's tile.

        Taken from asset metadata; tuple is (w-lon, e-lon, s-lat, n-lat),
        in degrees.  Structure for the lat/lons in INSPIRE.xml is, deep
        in the file:
            <gmd:EX_GeographicBoundingBox>
                <gmd:westBoundLongitude>
                    <gco:Decimal>-71.46678204877877</gco:Decimal>
                </gmd:westBoundLongitude>
                . . . and so on for 3 more values . . .
            </gmd:EX_GeographicBoundingBox>
        """
        # TODO this will have to be adapted for 'original' as the lat-lon can't be specific to a
        # tile:
        gmd = '{http://www.isotc211.org/2005/gmd}' # xml namespace foolishness
        gco = '{http://www.isotc211.org/2005/gco}'
        gbb_elem = self.xml_subtree('inspire', gmd + 'EX_GeographicBoundingBox')
        return tuple(float(gbb_elem.find(gmd + s).find(gco + 'Decimal').text) for s in (
                'westBoundLongitude', 'eastBoundLongitude',
                'southBoundLatitude', 'northBoundLatitude',
        ))


    #def gridded_zenith_angle(self):
    #    """Loads and returns zenith angle from the asset metadata.
    #
    #    These are stored in MTD_TL.xml, in degrees, at 5km x 5km resolution.
    #    """
    #    asset_contents = self.datafiles()
    #    # python idiom for "first item in list that satisfies a condition"; should only be one
    #    metadata_fn = next(n for n in asset_contents if re.match('^.*/GRANULE/.*/MTD_TL.xml$', n))
    #    with zipfile.ZipFile(self.filename) as asset_zf:
    #        with asset_zf.open(metadata_fn) as metadata_zf:
    #            tree = ElementTree.parse(metadata_zf)
    #            sag_elem = next(tree.iter('Sun_Angles_Grid')) # should only be one
    #            values_tags = sag_elem.find('Zenith').find('Values_List').findall('VALUES')
    #            text_rows = [vt.text for vt in values_tags]
    #            zenith_grid = []
    #            for tr in text_rows:
    #                numerical_row = [float(t) for t in tr.split()]
    #                zenith_grid.append(numerical_row)
    #    return zenith_grid


    def radiance_factors(self):
        """Computes values needed for converting L1C to TOA radiance.

        Sentinel-2's L1C is a TOA reflectance product.  That can be
        reverted to a TOA radiance product by multiplying each data
        point by a constant factor.  The factor is constant for each
        band of a given asset; the ordering in the returned list is the
        same as the order of the bands in _sensors given above.  See:
        https://sentinel.esa.int/web/sentinel/technical-guides/sentinel-2-msi/level-1c/algorithm
        """
        mza = math.radians(self.mean_solar_angle('zenith'))
        solar_irrads = self.solar_irradiances()
        julian_date = utils.julian_date(datetime.datetime.combine(self.date, self.time), 'cnes')
        return [(1 - 0.01673 * math.cos(0.0172 * (julian_date - 2)))**-2 # solar distance term
                * math.cos(mza) / math.pi # solar angle term
                * si # "equivalent extra-terrestrial solar spectrum" term; aka solar irradiance
                / 1000.0 # revert scaling factor so 16-bit ints aren't overflowed
                for si in solar_irrads]


    def generate_atmo_corrector(self):
        """Generate & return a SIXS object appropriate for this asset.

        Re-usees a previously created object if possible.
        """
        if hasattr(self, '_atmo_corrector'):
            utils.verbose_out('Found existing atmospheric correction object, reusing it.', 4)
            return self._atmo_corrector
        utils.verbose_out('Generating atmospheric correction object.', 4)
        sensor_md = self._sensors[self.sensor]
        visbands = sensor_md['indices-colors'] # TODO visbands isn't really the right name
        vb_indices = [sensor_md['colors'].index(vb) for vb in visbands]
        # assemble list of relevant band boundaries
        wvlens = [sensor_md['bandbounds'][i] for i in vb_indices]
        # assemble geometries
        (viewing_zn, viewing_az) = self.mean_viewing_angle()
        (solar_zn, solar_az) = self.mean_solar_angle()
        (w_lon, e_lon, s_lat, n_lat) = self.tile_lat_lon()
        geo = {
            'zenith': viewing_zn,
            'azimuth': viewing_az,
            'solarzenith': solar_zn,
            'solarazimuth': solar_az,
            'lon': (w_lon + e_lon) / 2.0, # copy landsat - use center of tile
            'lat': (s_lat + n_lat) / 2.0, # copy landsat - use center of tile
        }
        dt = datetime.datetime.combine(self.date, self.time)
        self._atmo_corrector = atmosphere.SIXS(visbands, wvlens, geo, dt, sensor=self.sensor)
        return self._atmo_corrector


class sentinel2Data(Data):
    name = 'Sentinel2'
    version = '0.1.0'
    Asset = sentinel2Asset

    _asset_type = 'L1C' # only one for the whole driver for now

    _productgroups = {
        'Index': ['ndvi', 'evi', 'lswi', 'ndsi', 'bi', 'satvi', 'msavi2', 'vari', 'brgt',
                  'ndti', 'crc', 'crcm', 'isti', 'sti'] # <-- tillage indices
    }
    _products = {
        # standard products
        'rad': {
            'description': 'Surface-leaving radiance',
            'assets': ['L1C'],
        },
        'ref': {
            'description': 'Surface reflectance',
            'assets': ['L1C'],
        },
        # index products
        'ndvi': {
            'description': 'Normalized Difference Vegetation Index',
            'assets': ['L1C'],
        },
        'evi': {
            'description': 'Enhanced Vegetation Index',
            'assets': ['L1C'],
        },
        'lswi': {
            'description': 'Land Surface Water Index',
            'assets': ['L1C'],
        },
        'ndsi': {
            'description': 'Normalized Difference Snow Index',
            'assets': ['L1C'],
        },
        'bi': {
            'description': 'Brightness Index',
            'assets': ['L1C'],
        },
        'satvi': {
            'description': 'Soil-Adjusted Total Vegetation Index',
            'assets': ['L1C'],
        },
        'msavi2': {
            'description': 'Modified Soil-adjusted Vegetation Index',
            'assets': ['L1C'],
        },
        'vari': {
            'description': 'Visible Atmospherically Resistant Index',
            'assets': ['L1C'],
        },
        # index products related to tillage
        'brgt': {
            'description': ('VIS and NIR reflectance, weighted by solar energy distribution.'),
            # rbraswell's original description:
            #'description': ('Brightness index:  Visible to near infrared reflectance weighted by'
            #                ' approximate energy distribution of the solar spectrum. A proxy for'
            #                ' broadband albedo.'),
            'assets': ['L1C'],
        },
        'ndti': {
            'description': 'Normalized Difference Tillage Index',
            'assets': ['L1C'],
        },
        'crc': {
            'description': 'Crop Residue Cover (uses BLUE)',
            'assets': ['L1C'],
        },
        'crcm': {
            'description': 'Crop Residue Cover, Modified (uses GREEN)',
            'assets': ['L1C'],
        },
        'isti': {
            'description': 'Inverse Standard Tillage Index',
            'assets': ['L1C'],
        },
        'sti': {
            'description': 'Standard Tillage Index',
            'assets': ['L1C'],
        },
    }
    _product_dependencies = {
        'indices':      'ref',
        'indices-toa':  'ref-toa',
        'ref':          'rad-toa',
        'rad':          'rad-toa',
        'rad-toa':      'ref-toa',
        'ref-toa':      None, # has no deps but the asset
    }

    def plan_work(self, requested_products, overwrite):
        """Plan processing run using requested products & their dependencies.

        Returns a set of processing steps needed to generate
        requested_products.  For instance, 'rad-toa' depends on
        'ref-toa', so if the user requests 'rad-toa', set(['rad-toa',
        'ref-toa']) is returned.  But if 'ref-toa' is already in the
        inventory, it is omitted, unless overwrite is True.
        requested_products should contain strings matching
        _product_dependencies above.
        """
        surf_indices = self._productgroups['Index']
        toa_indices  = [i + '-toa' for i in self._productgroups['Index']]
        _pd = self._product_dependencies
        work = set()
        for rp in requested_products:
            # handle indices specially
            if rp in surf_indices:
                prereq = 'indices'
            elif rp in toa_indices:
                prereq = 'indices-toa'
            else:
                prereq = rp
            # go thru each prereq and add it in if it's not already present, respecting overwrite.
            while prereq in _pd and (overwrite or prereq not in self.products):
                work.add(prereq)
                prereq = _pd[prereq]
        return work

    def current_asset(self):
        return self.assets[self._asset_type]

    def current_sensor(self):
        return self.sensors[self._asset_type]


    def load_image(self, product):
        """Load a product file into a GeoImage and return it

        The GeoImage is instead fetched from a cache if possible.
        (sensor, product) should match an entry from self.filenames.
        """
        if product in self._product_images:
            return self._product_images[product]
        image = gippy.GeoImage(self.filenames[(self.current_sensor(), product)])
        self._product_images[product] = image
        return image


    @classmethod
    def normalize_tile_string(cls, tile_string):
        """Sentinel-2 customized tile-string normalizer.

        Raises an exception if the tile string doesn't match MGRS
        format, and converts the tile string to uppercase.
        """
        if not re.match(r'^\d\d[a-zA-Z]{3}$', tile_string):
            err_msg = "Tile string '{}' doesn't match MGRS format (eg '04QFJ')".format(tile_string)
            raise IOError(err_msg)
        return tile_string.upper()


    @classmethod
    def meta_dict(cls):
        """Assemble GIPS & driver version for embedding in output files."""
        meta = super(sentinel2Data, cls).meta_dict()
        meta['GIPS-sentinel2 Version'] = cls.version
        return meta

    def load_metadata(self):
        """Ingest metadata from asset files; just raster filenames presently."""
        if hasattr(self, 'metadata'):
            return # nothing to do if metadata is already loaded

        # only one asset type supported for this driver so for now hardcoding is ok
        asset_type = 'L1C'
        datafiles = self.assets[asset_type].datafiles()

        # restrict filenames known to just the raster layers
        asset = self.current_asset()
        raster_fn_pat = asset.style_res['raster-re'].format(tileid=asset.tile)
        fnl = [df for df in datafiles if re.match(raster_fn_pat, df)]
        # have to sort the list or else gippy will get confused about which band is which
        band_strings = sentinel2Asset._sensors[self.sensors[asset_type]]['band-strings']
        # sorting is weird because the bands aren't named consistently
        fnl.sort(key=lambda f: band_strings.index(f[-6:-4]))
        self.metadata = {'filenames': fnl}

    def read_raw(self):
        """Read in bands using original SAFE asset file (a .zip)."""
        self.load_metadata()

        if utils.settings().REPOS[self.Repository.name.lower()].get('extract', False):
            # Extract files to disk
            datafiles = self.assets['L1C'].extract(self.metadata['filenames'])
        else:
            # Use zipfile directly using GDAL's virtual filesystem
            datafiles = [os.path.join('/vsizip/' + self.assets['L1C'].filename, f)
                    for f in self.metadata['filenames']]
        self.metadata['abs-filenames'] = datafiles

        # TODO unused here down?
        image = gippy.GeoImage(datafiles)
        image.SetNoData(0) # inferred rather than taken from spec
        sensor = self.assets['L1C'].sensor
        colors = self.assets['L1C']._sensors[sensor]['colors']

        # go through all the files/bands in the image object and set values for each one
        for i, color in zip(range(1, len(colors) + 1), colors):
            image.SetBandName(color, i)

        return image


    def _time_report(self, msg, reset_clock=False, verbosity=None):
        """Provide the user with progress reports, including elapsed time.

        Reset elapsed time with reset_clock=True; when starting or
        resetting the clock, specify a verbosity, or else accept the
        default of 3.
        """
        start = getattr(self, '_time_report_start', None)
        if reset_clock or start is None:
            start = self._time_report_start = datetime.datetime.now()
            self._time_report_verbosity = 3 if verbosity is None else verbosity
        elif verbosity is not None:
            raise ValueError('Changing verbosity is only permitted when resetting the clock')
        utils.verbose_out('{}:  {}'.format(datetime.datetime.now() - start, msg),
                self._time_report_verbosity)


    def ref_toa_geoimage(self, sensor, data_spec):
        """Make a proto-product which acts as a basis for several products.

        It is equivalent to ref-toa; it's needed because the asset's
        spatial resolution must be resampled to be equal for all bands
        of interest.  Due to equivalence with ref-toa, if that product
        exists in the filesystem, it's opened and returned in a GeoImage
        instead of newly upsampled data.
        """
        # TODO data_spec can be refactored out of argslist; only depends on self & asset_type ('L1C')
        self._time_report('Starting upsample of Sentinel-2 asset bands')
        # TODO this upsamples everything, when only two bands need it.  The first attempt to remedy
        # this was actually slower, however; see branch 200-optimize-upsampling, commit 2e97ba0.
        # compile a list of the files needed for the proto-product
        src_filenames = [f for f in self.metadata['abs-filenames']
                if f[-6:-4] in data_spec['indices-bands']]
        # upsample each one in turn (some don't need it but do them all for simplicity)
        with utils.make_temp_dir() as tmpdir:
            upsampled_filenames = [os.path.join(tmpdir, os.path.basename(f) + '.tif')
                    for f in src_filenames]
            for in_fn, out_fn in zip(src_filenames, upsampled_filenames):
                cmd_str = 'gdalwarp -tr 10 10 {} {}'.format(in_fn, out_fn)
                cmd_args = shlex.split(cmd_str)
                self._time_report('Upsampling:  ' + cmd_str)
                p = subprocess.Popen(cmd_args)
                p.communicate()
                if p.returncode != 0:
                    raise IOError("Expected gdalwarp exit status 0, got {}".format(
                            p.returncode))
            upsampled_img = gippy.GeoImage(upsampled_filenames)
            upsampled_img.SetMeta(self.meta_dict())
            upsampled_img.SetNoData(0)
            for band_num, band_string in enumerate(data_spec['indices-bands'], 1):
                band_index = data_spec['band-strings'].index(band_string) # starts at 0
                color_name = data_spec['colors'][band_index]
                upsampled_img.SetBandName(color_name, band_num)
        self._product_images['ref-toa'] = upsampled_img
        self._time_report('Completed upsampling of Sentinel-2 asset bands')


    def rad_toa_geoimage(self, asset_type, sensor):
        """Reverse-engineer TOA ref data back into a TOA radiance product.

        This is used as intermediary data but is congruent to the rad-toa
        product.
        """
        self._time_report('Starting reversion to TOA radiance.')
        upsampled_img = self.load_image('ref-toa')
        asset_instance = self.assets[asset_type] # sentinel2Asset
        colors = asset_instance._sensors[sensor]['colors']

        radiance_factors = asset_instance.radiance_factors()

        rad_image = gippy.GeoImage(upsampled_img)

        for i in range(len(rad_image)):
            color = rad_image[i].Description()
            rf = radiance_factors[colors.index(color)]
            self._time_report(
                'TOA radiance reversion factor for {} (band {}): {}'.format(color, i + 1, rf))
            rad_image[i] = rad_image[i] * rf
        rad_image.SetNoData(0)
        self._product_images['rad-toa'] = rad_image


    def rad_geoimage(self):
        """Transmute TOA radiance product into a surface radiance product."""
        self._time_report('Setting up for converting radiance from TOA to surface')
        rad_toa_img = self.load_image('rad-toa')
        ca = self.current_asset()
        atm6s = ca.generate_atmo_corrector()

        rad_image = gippy.GeoImage(rad_toa_img)
        # set meta to pass along to indices
        rad_image._aod_source = str(atm6s.aod[0])
        rad_image._aod_value  = str(atm6s.aod[1])

        for c in ca._sensors[self.current_sensor()]['indices-colors']:
            (T, Lu, Ld) = atm6s.results[c] # Ld is unused for this product
            rad_image[c] = (rad_toa_img[c] - Lu) / T
        self._product_images['rad'] = rad_image


    def process_indices(self, mode, sensor, filename_prefix, indices):
        """Generate the given indices.

        gippy.algorithms.Indices is called for the given indices, using
        an image appropriate for the given mode ('toa' or not).
        """
        if len(indices) == 0:
            return

        self._time_report('Starting indices processing for: {}'.format(indices.keys()))

        metadata = self.meta_dict()
        if mode != 'toa':
            image = self.load_image('ref')
            # this faff is needed because gippy shares metadata across images behind your back
            metadata['AOD Source'] = getattr(image, '_aod_source', image.Meta('AOD Source'))
            metadata['AOD Value']  = getattr(image, '_aod_value',  image.Meta('AOD Value'))
        else:
            image = self.load_image('ref-toa')

        # fnames = mapping of product-to-output-filenames, minus filename extension (probably .tif)
        # reminder - indices' values are the keys, split by hyphen, eg {ndvi-toa': ['ndvi', 'toa']}
        fnames = {indices[key][0]: filename_prefix + key + '.tif' for key in indices}
        prodout = gippy.algorithms.Indices(image, fnames, metadata)
        [self.AddFile(sensor, key, fname) for key, fname in zip(indices, prodout.values())]
        self._time_report(' -> %s: processed %s' % (self.basename, indices))


    def ref_geoimage(self, asset_type, sensor):
        """Generate a surface reflectance image.

        Made from a rad-toa image (the reverted ref-toa data sentinel-2 L1C
        provides), put through an atmospheric correction process.  CF landsat.
        """
        self._time_report('Computing atmospheric corrections for surface reflectance')
        atm6s = self.assets[asset_type].generate_atmo_corrector()
        scaling_factor = 0.001 # to prevent chunky small ints
        rad_rev_img = self.load_image('rad-toa')
        sr_image = gippy.GeoImage(rad_rev_img)
        # set meta to pass along to indices
        sr_image._aod_source = str(atm6s.aod[0])
        sr_image._aod_value  = str(atm6s.aod[1])
        for c in self.assets[asset_type]._sensors[sensor]['indices-colors']:
            (T, Lu, Ld) = atm6s.results[c]
            TLdS = T * Ld * scaling_factor # don't do it every pixel; believed to be faster
            sr_image[c] = (rad_rev_img[c] - Lu) / TLdS
        self._product_images['ref'] = sr_image


    def process(self, products=None, overwrite=False, **kwargs):
        """Produce data products and save them to files.

        If `products` is None, it processes all products.  If
        `overwrite` is True, it will overwrite existing products if they
        are found.  Products are saved to a well-known or else specified
        directory.  kwargs is unused, and is present for compatibility.
        """
        asset_type = 'L1C' # only one in the driver for now, conveniently
        self._time_report('Starting processing for this temporal-spatial unit')
        products = self.needed_products(products, overwrite)
        if len(products) == 0:
            utils.verbose_out('No new processing required.')
            return
        self._product_images = {}
        # construct as much of the product filename as we can right now
        filename_prefix = os.path.join(
                self.path, self.basename + '_' + self.sensors[asset_type] + '_')

        # Read the assets
        with utils.error_handler('Error reading '
                                 + utils.basename(self.assets[asset_type].filename)):
            self.read_raw() # returns a GeoImage, presently unused

        sensor = self.sensors[asset_type]
        # dict describing specification for all the bands in the asset
        data_spec = self.assets[asset_type]._sensors[sensor]

        work = self.plan_work(products.requested.keys(), overwrite) # see if we can save any work

        # TODO here down unsure if safe for 'original' style assets

        # only do the bits that need doing
        if 'ref-toa' in work:
            self.ref_toa_geoimage(sensor, data_spec)
        if 'rad-toa' in work:
            self.rad_toa_geoimage(asset_type, sensor)
        if 'rad' in work:
            self.rad_geoimage()
        if 'ref' in work:
            self.ref_geoimage(asset_type, sensor)

        self._time_report('Starting on standard product processing')

        # Process standard products
        for key, val in products.groups()['Standard'].items():
            err_msg = 'Error creating product {} for {}'.format(
                    key, os.path.basename(self.assets[asset_type].filename))
            with utils.error_handler(err_msg, continuable=True):
                self._time_report('Starting {} processing'.format(key))
                filename = filename_prefix + key + '.tif'

                # have to reproduce the whole object because gippy refuses to write metadata when
                # you do image.Process(filename).
                try:
                    source_image = self._product_images[key]
                    output_image = gippy.GeoImage(filename, source_image)
                    output_image.SetNoData(0)
                    output_image.SetMeta(self.meta_dict()) # add standard metadata
                    if key in ('ref', 'rad'): # atmo-correction metadata
                        output_image.SetMeta('AOD Source', source_image._aod_source)
                        output_image.SetMeta('AOD Value',  source_image._aod_value)
                    for b_num, b_name in enumerate(source_image.BandNames(), 1):
                        output_image.SetBandName(b_name, b_num)
                    # process bandwise because gippy had an error doing it all at once
                    for i in range(len(source_image)):
                        source_image[i].Process(output_image[i])
                    self.AddFile(sensor, key, filename)
                except Exception:
                    utils.remove_files([filename])
                    raise

            self._time_report('Finished {} processing'.format(key))
            (source_image, output_image) = (None, None) # gc hint due to C++/swig weirdness
        self._time_report('Completed standard product processing')

        # process indices in two groups:  toa and surf
        indices = products.groups()['Index']
        toa_indices  = {k: v for (k, v) in indices.items() if 'toa' in v}
        self.process_indices('toa', sensor, filename_prefix, toa_indices)

        surf_indices  = {k: v for (k, v) in indices.items() if 'toa' not in v}
        self.process_indices('surf', sensor, filename_prefix, surf_indices)

        self._product_images = {} # hint for gc; may be needed due to C++/swig weirdness
        self._time_report('Processing complete for this spatial-temporal unit')