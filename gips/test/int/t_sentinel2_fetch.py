"""Integration tests for sentinel2Asset.fetch and its friends."""

import os
import shutil
import datetime
import subprocess

import pytest

from ...data.sentinel2 import sentinel2

dt = datetime.datetime

# recorded from a real call: sentinel2.sentinel2Asset.fetch('L1C', '19TCH', dt(2016, 1, 19, 0, 0))
json_response = """{"feed": {
   "xmlns:opensearch": "http://a9.com/-/spec/opensearch/1.1/",
   "link": [
      {
         "rel": "self",
         "type": "application/atom+xml",
         "href": "https://scihub.copernicus.eu/dhus/search?q=filename:S2?_OPER_PRD_MSIL1C_*_20160119T??????.SAFE AND footprint:\\"Intersects(42.8429011066, -70.781045648)\\"&start=0&rows=10"
      },
      {
         "rel": "first",
         "type": "application/atom+xml",
         "href": "https://scihub.copernicus.eu/dhus/search?q=filename:S2?_OPER_PRD_MSIL1C_*_20160119T??????.SAFE AND footprint:\\"Intersects(42.8429011066, -70.781045648)\\"&start=0&rows=10"
      },
      {
         "rel": "last",
         "type": "application/atom+xml",
         "href": "https://scihub.copernicus.eu/dhus/search?q=filename:S2?_OPER_PRD_MSIL1C_*_20160119T??????.SAFE AND footprint:\\"Intersects(42.8429011066, -70.781045648)\\"&start=0&rows=10"
      },
      {
         "rel": "search",
         "type": "application/opensearchdescription+xml",
         "href": "opensearch_description.xml"
      }
   ],
   "xmlns": "http://www.w3.org/2005/Atom",
   "opensearch:itemsPerPage": 10,
   "id": "https://scihub.copernicus.eu/dhus/search?q=filename:S2?_OPER_PRD_MSIL1C_*_20160119T??????.SAFE AND footprint:\\"Intersects(42.8429011066, -70.781045648)\\"",
   "author": {"name": "Sentinels Scientific Data Hub"},
   "title": "Sentinels Scientific Data Hub search results for: filename:S2?_OPER_PRD_MSIL1C_*_20160119T??????.SAFE AND footprint:\\"Intersects(42.8429011066, -70.781045648)\\"",
   "updated": "2017-03-29T19:44:57.724Z",
   "opensearch:totalResults": 1,
   "entry": {
      "summary": "Date: 2016-01-19T15:54:47Z, Instrument: MSI, Mode: , Satellite: Sentinel-2, Size: 7.23 GB",
      "id": "0b30e2da-d0d9-4438-889a-806275957811",
      "title": "S2A_OPER_PRD_MSIL1C_PDMC_20160119T230435_R011_V20160119T155447_20160119T155447",
      "str": [
         {
            "content": "T",
            "name": "processed"
         },
         {
            "content": "S2A_OPER_PRD_MSIL1C_PDMC_20160119T230435_R011_V20160119T155447_20160119T155447.SAFE",
            "name": "filename"
         },
         {
            "content": "<gml:Polygon srsName=\\"http://www.opengis.net/gml/srs/epsg.xml#4326\\" xmlns:gml=\\"http://www.opengis.net/gml\\">\\n   <gml:outerBoundaryIs>\\n      <gml:LinearRing>\\n         <gml:coordinates>42.40755077889176,-75.00024305568395 41.50699135756072,-75.00023965746524 40.56274991351036,-75.00023625343321 40.555797113096865,-73.761101247307 40.537104618892954,-72.58083437128185 40.53610084869193,-72.54231488874747 40.50846282585221,-72.54082260253305 40.5219935363238,-72.00094957244386 40.50488583658978,-71.34444498559898 40.538494307869534,-71.34257161424908 40.53946365222692,-71.30389494043206 40.55783709926159,-70.06541547567338 41.45868111794904,-70.08005997957456 41.45868161365336,-70.08002716016999 41.50191368368469,-70.08076278656938 41.54675876989539,-70.08149180738357 41.54675825481533,-70.08152585089569 42.358839383207,-70.09534402606192 42.35883991770658,-70.09530924716697 42.40231105256133,-70.09608372942517 42.44744302996698,-70.09685168418682 42.447442474121026,-70.09688779137116 43.34744038882545,-70.11292216497769 43.32624633586569,-71.46678204877877 43.29688477143789,-71.46562286353989 43.32292344682087,-72.41249086350852 43.323576596360866,-72.41246381589346 43.32458957798057,-72.473077903965 43.326256971778115,-72.53371085886853 43.325603306094344,-72.53373666022858 43.34418419228872,-73.6455667767175 43.34483481646454,-73.64555267001921 43.345191903390365,-73.70586549120344 43.346200009839855,-73.76618786223797 43.3455491229698,-73.7662007178937 43.35285539234588,-75.00024679052602 42.40755077889176,-75.00024305568395<\\/gml:coordinates>\\n      <\\/gml:LinearRing>\\n   <\\/gml:outerBoundaryIs>\\n<\\/gml:Polygon>",
            "name": "gmlfootprint"
         },
         {
            "content": "SAFE",
            "name": "format"
         },
         {
            "content": "S2A_OPER_PRD_MSIL1C_PDMC_20160119T230435_R011_V20160119T155447_20160119T155447",
            "name": "identifier"
         },
         {
            "content": "MSI",
            "name": "instrumentshortname"
         },
         {
            "content": "INS-NOBS",
            "name": "sensoroperationalmode"
         },
         {
            "content": "Multi-Spectral Instrument",
            "name": "instrumentname"
         },
         {
            "content": "POLYGON ((-75.00024305568395 42.40755077889176,-75.00023965746524 41.50699135756072,-75.00023625343321 40.56274991351036,-73.761101247307 40.555797113096865,-72.58083437128185 40.537104618892954,-72.54231488874747 40.53610084869193,-72.54082260253305 40.50846282585221,-72.00094957244386 40.5219935363238,-71.34444498559898 40.50488583658978,-71.34257161424908 40.538494307869534,-71.30389494043206 40.53946365222692,-70.06541547567338 40.55783709926159,-70.08005997957456 41.45868111794904,-70.08002716016999 41.45868161365336,-70.08076278656938 41.50191368368469,-70.08149180738357 41.54675876989539,-70.08152585089569 41.54675825481533,-70.09534402606192 42.358839383207,-70.09530924716697 42.35883991770658,-70.09608372942517 42.40231105256133,-70.09685168418682 42.44744302996698,-70.09688779137116 42.447442474121026,-70.11292216497769 43.34744038882545,-71.46678204877877 43.32624633586569,-71.46562286353989 43.29688477143789,-72.41249086350852 43.32292344682087,-72.41246381589346 43.323576596360866,-72.473077903965 43.32458957798057,-72.53371085886853 43.326256971778115,-72.53373666022858 43.325603306094344,-73.6455667767175 43.34418419228872,-73.64555267001921 43.34483481646454,-73.70586549120344 43.345191903390365,-73.76618786223797 43.346200009839855,-73.7662007178937 43.3455491229698,-75.00024679052602 43.35285539234588,-75.00024305568395 42.40755077889176))",
            "name": "footprint"
         },
         {
            "content": "GS2A_20160119T154552_003011_N02.01",
            "name": "s2datatakeid"
         },
         {
            "content": "2015-000A",
            "name": "platformidentifier"
         },
         {
            "content": "DESCENDING",
            "name": "orbitdirection"
         },
         {
            "content": "Sentinel-2A",
            "name": "platformserialidentifier"
         },
         {
            "content": "02.01",
            "name": "processingbaseline"
         },
         {
            "content": "Level-1C",
            "name": "processinglevel"
         },
         {
            "content": "S2MSI1C",
            "name": "producttype"
         },
         {
            "content": "Sentinel-2",
            "name": "platformname"
         },
         {
            "content": "7.23 GB",
            "name": "size"
         }
      ],
      "int": [
         {
            "content": 3011,
            "name": "orbitnumber"
         },
         {
            "content": 11,
            "name": "relativeorbitnumber"
         }
      ],
      "link": [
         {"href": "https://scihub.copernicus.eu/dhus/odata/v1/Products('0b30e2da-d0d9-4438-889a-806275957811')/$value"},
         {
            "rel": "alternative",
            "href": "https://scihub.copernicus.eu/dhus/odata/v1/Products('0b30e2da-d0d9-4438-889a-806275957811')/"
         },
         {
            "rel": "icon",
            "href": "https://scihub.copernicus.eu/dhus/odata/v1/Products('0b30e2da-d0d9-4438-889a-806275957811')/Products('Quicklook')/$value"
         }
      ],
      "date": [
         {
            "content": "2016-01-19T22:54:23.222Z",
            "name": "ingestiondate"
         },
         {
            "content": "2016-01-19T15:54:47Z",
            "name": "beginposition"
         },
         {
            "content": "2016-01-19T15:54:47Z",
            "name": "endposition"
         }
      ],
      "double": {
         "content": 35.285714285714285,
         "name": "cloudcoverpercentage"
      }
   },
   "subtitle": "Displaying 1 results. Request done in 0.01 seconds.",
   "opensearch:startIndex": 0,
   "opensearch:Query": {
      "searchTerms": "filename:S2?_OPER_PRD_MSIL1C_*_20160119T??????.SAFE AND footprint:\\"Intersects(42.8429011066, -70.781045648)\\"",
      "role": "request",
      "startPage": 1
   }
}}
"""

expected_tiles = [
    '18TXK', '18SVA', '18SWJ', '18SXJ', '18SUA', '18SWH', '18SXH', '18SWB', '18SWG', '18SXG',
    '18SVB', '18SWF', '19TCL', '19TBG', '18SVE', '18SWE', '18SVD', '18SWD', '18SWC', '18SVC',
    '18TYR', '18RVV', '18TYL', '18TYQ', '18TXL', '18TYS', '18TYM', '18RUV', '18TXM', '19TBF',
    '18TYN', '18TYP', '18TXN', '19TCK', '19TCJ', '18SXF', '18TXP', '18TYK', '18TWK', '19TCM',
    '18SVF', '19TBE', '18SUB', '18SWA', '18TXQ', '18SXE', '19TCH', '18SYJ', '18TWL', '18RVU',
    '19TDL', '18SVG', '18SUC', '18RWV', '18TXR', '19TDM', '19SBD', '18SXD', '18SYH', '19TCG',
    '18TWM', '18RUU', '18SVH', '19TDK', '18TXS', '18SUD', '18RTV', '18RWU', '18SXC', '18SYG',
    '19SBC', '18TWN', '19TCF', '18SVJ', '18RTU', '18SUE', '18STA', '19TDJ', '18TYT', '18SXB',
    '18SYF', '18TWP', '18TXT', '19SBB', '18TVK', '19TCN', '19TCE', '18SUF', '19TEM', '18STB',
    '18SXA',
]

test_asset_bn = 'S2A_OPER_PRD_MSIL1C_PDMC_20160119T230435_R011_V20160119T155447_20160119T155447.zip'

@pytest.fixture
def test_asset_fn():
    return os.path.join(os.path.dirname(__file__), 'data', test_asset_bn)

@pytest.fixture
def fetch_mocks(mocker, test_asset_fn):
    """Mock file-fetching wget Popen:"""

    # Popen is called once to get a listing of files then again when one is
    # chosen to download.
    real_popen = subprocess.Popen
    real_pipe = subprocess.PIPE

    m_subprocess = mocker.patch.object(sentinel2, 'subprocess')
    m_subprocess.PIPE = real_pipe # need to stay 'real'
    m_popen = m_subprocess.Popen
    m_popen_rv = mocker.Mock()
    m_popen_rv.returncode = 0

    def second_call(args):
        """Fake the download by copying a file into place."""
        od_option = next(a for a in args if a.startswith('--output-document'))
        _, downloaded_asset_fn = od_option.split('=')
        shutil.copy(test_asset_fn, downloaded_asset_fn)
        return m_popen_rv

    def first_call(*args, **kwargs):
        """Fake the search by returning a recorded outcome."""
        m_popen.side_effect = second_call
        m_popen_rv.communicate.return_value = (json_response, 'i am fake stderr')
        return m_popen_rv

    m_popen.side_effect = first_call

    return m_popen


def t_fetch_old_asset(fetch_mocks):
    """Integration test for sentinel2Asset.fetch.

    Uses the test semi-real asset in data/ for this purpose.
    """
    # setup & mocks
    expected_staged_bns = set([t + '_' + test_asset_bn for t in expected_tiles])
    stage_path = sentinel2.sentinel2Repository.path('stage')
    # check for possible interference in the stage directory
    obstacles = expected_staged_bns.intersection(set(os.listdir(stage_path)))
    if len(obstacles) > 0:
        raise IOError('Cannot run test:  {} items in the way: {}'.format(
            len(obstacles), obstacles))

    # call, assertion, cleanup
    try:
        sentinel2.sentinel2Asset.fetch('L1C', '19TCH', dt(2016, 1, 19))
        actual = set(os.listdir(stage_path))
        assert expected_staged_bns.issubset(actual)
    finally:
        for f in expected_staged_bns:
            full_fn = os.path.join(stage_path, f)
            os.path.exists(full_fn) and os.remove(full_fn)


def t_fetch_old_asset_duplicate(fetch_mocks, mocker):
    """Integration test for sentinel2Asset.fetch.

    Checks that assets aren't downloaded when it's clear they're already
    in the stage.  Uses the test semi-real asset in data/ for this
    purpose.
    """
    # setup & mocks
    stage_path = sentinel2.sentinel2Repository.path('stage')
    staged_bn = '19TCH_' + test_asset_bn
    staged_fn = os.path.join(stage_path, staged_bn)

    if os.path.exists(staged_fn):
        raise IOError('Cannot run test:  item in the way: ' + staged_bn)
    open(staged_fn, 'a').close() # python idiom for `touch`

    m_popen = fetch_mocks # for asserting 2nd call (download) was not made
    m_mkdtemp = mocker.patch.object(sentinel2.tempfile, 'mkdtemp')

    # call, assertion, cleanup
    try:
        sentinel2.sentinel2Asset.fetch('L1C', '19TCH', dt(2016, 1, 19))
        assert (m_popen.call_count, m_mkdtemp.call_count) == (1, 0)
    finally:
        os.path.exists(staged_fn) and os.remove(staged_fn)


def t_tile_list(test_asset_fn):
    """Use the test asset file to confirm tile_list()."""
    tiles = sentinel2.sentinel2Asset.tile_list(test_asset_fn)
    assert expected_tiles == tiles


@pytest.fixture
def archive_setup(test_asset_fn):
    """Set up to archive test_asset_fn.

    Make sure tiles/ is clear.  Copy the asset into the stage.
    Clean it out from stage/ and tiles/ afterwards.
    """
    # set up source & destination filesystem paths
    stage_path = sentinel2.sentinel2Repository.path('stage')
    tiles_path = sentinel2.sentinel2Repository.path('tiles')

    staged_asset_bn = '19TCH_' + test_asset_bn

    staged_asset_fn   = os.path.join(stage_path, staged_asset_bn)
    archived_asset_fn = os.path.join(tiles_path, '19TCH', '2016019', staged_asset_bn)

    # do some pre-test checks
    if os.path.exists(staged_asset_fn):
        raise IOError('`{}` exists, aborting'.format(staged_asset_fn))
    if os.path.exists(archived_asset_fn):
        raise IOError('`{}` exists, aborting'.format(archived_asset_fn))

    # finish setup by moving the asset into the stage
    shutil.copy(test_asset_fn, staged_asset_fn)

    # let the test run
    try:
        yield (stage_path, staged_asset_fn, archived_asset_fn)
    finally:
        # clean up by removing the asset from both the stage and the archive
        os.path.exists(staged_asset_fn) and os.remove(staged_asset_fn)
        os.path.exists(archived_asset_fn) and os.remove(archived_asset_fn)


def t_archive_old_asset(archive_setup):
    """Confirm old-style assets archive properly."""
    stage_path, staged_asset_fn, archived_asset_fn = archive_setup

    archived_assets = sentinel2.sentinel2Asset.archive(stage_path)

    assert os.path.exists(archived_asset_fn) and not os.path.exists(staged_asset_fn)


def t_stage_asset_old_style(test_asset_fn):
    """Confirm old-style assets are tile-exploded into stage/ properly."""
    # setup
    stage_path = sentinel2.sentinel2Repository.path('stage')
    expected_files = [os.path.join(stage_path, t + '_' + test_asset_bn) for t in expected_tiles]
    # safety check
    extant_files = [ef for ef in expected_files if os.path.exists(ef)]
    if len(extant_files) > 0:
        raise IOError("Files exist, aborting: {}".format(extant_files))

    try:
        sentinel2.sentinel2Asset.stage_asset('original', test_asset_fn, test_asset_bn)
        actual_files = [ef for ef in expected_files if os.path.exists(ef)]
        assert expected_files == actual_files
    finally:
        # clean up in any case; this may break depending on what went wrong
        [os.path.exists(ef) and os.remove(ef) for ef in expected_files]