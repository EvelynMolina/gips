
import collections

import pytest

from .. import util

from . import modis_process
from . import merra_process
from . import sentinel2_process
from . import hls_process
from . import landsat_process

expectations = {}

# set up lite test marks
lite_mark_spec = { k: util.lite for k in [
    # consensus is that merra, chirps, & daymet don't need to be tested here
    ('modis', 'ndvi'),
    ('landsat', 'ndvi-toa'),
    ('sentinel2', 'evi-toa'),
    ('prism', 'ppt'),
    ('hls', 'ndvi'),
    #('sar', 'sign'), # TODO automate arttifact-* pytest.ini values
]}

mark_spec = lite_mark_spec.copy()

expectations['modis'] = modis_process.expectations
expectations['merra'] = merra_process.expectations

expectations['sentinel2'] = sentinel2_process.expectations
expectations['hls'] = hls_process.expectations
expectations['landsat'] = landsat_process.expectations

mark_spec['sentinel2'] = util.slow

# TODO some of these may be fast enough without --setup-repo
for k in (('landsat', 'bqashadow'), ('landsat', 'ref-toa'),
          ('landsat', 'rad-toa')):
    mark_spec[k] = util.slow

mark_spec[('landsat', 'cloudmask-coreg')] = pytest.mark.skip(
    'test not workable at the moment due to django db flush between tests, '
    'causing coreg not to find any local sentinel2 -- even though it is there.'
)

mark_spec[('landsat', 'bqashadow')] = pytest.mark.skip(
 'Deleted in branch but extant on dev; needs to be fixed post-merge.')


expectations['prism'] = collections.OrderedDict([
 # t_process[prism-tmin] recording:
 ('tmin',
  [('prism/tiles/CONUS/19821203/CONUS_19821203_prism_tmin.tif',
    'symlink',
    '/vsizip/',
    '/prism/tiles/CONUS/19821203/PRISM_tmin_stable_4kmD1_19821203_bil.zip/PRISM_tmin_stable_4kmD1_19821203_bil.bil'),
   ('prism/tiles/CONUS/19821202/CONUS_19821202_prism_tmin.tif',
    'symlink',
    '/vsizip/',
    '/prism/tiles/CONUS/19821202/PRISM_tmin_stable_4kmD1_19821202_bil.zip/PRISM_tmin_stable_4kmD1_19821202_bil.bil'),
   ('prism/tiles/CONUS/19821201/CONUS_19821201_prism_tmin.tif',
    'symlink',
    '/vsizip/',
    '/prism/tiles/CONUS/19821201/PRISM_tmin_stable_4kmD1_19821201_bil.zip/PRISM_tmin_stable_4kmD1_19821201_bil.bil')]),

 # t_process[prism-tmax] recording:
 ('tmax',
  [('prism/tiles/CONUS/19821201/CONUS_19821201_prism_tmax.tif',
    'symlink',
    '/vsizip/',
    '/prism/tiles/CONUS/19821201/PRISM_tmax_stable_4kmD1_19821201_bil.zip/PRISM_tmax_stable_4kmD1_19821201_bil.bil'),
   ('prism/tiles/CONUS/19821202/CONUS_19821202_prism_tmax.tif',
    'symlink',
    '/vsizip/',
    '/prism/tiles/CONUS/19821202/PRISM_tmax_stable_4kmD1_19821202_bil.zip/PRISM_tmax_stable_4kmD1_19821202_bil.bil'),
   ('prism/tiles/CONUS/19821203/CONUS_19821203_prism_tmax.tif',
    'symlink',
    '/vsizip/',
    '/prism/tiles/CONUS/19821203/PRISM_tmax_stable_4kmD1_19821203_bil.zip/PRISM_tmax_stable_4kmD1_19821203_bil.bil')]),

 # IMPORTANT NOTE pptsum seems to generate ppt products as part of
 # its function; as a result ppt products may exist already if pptsum
 # goes first.
 # t_process[prism-ppt] recording:
 ('ppt',
  [('prism/tiles/CONUS/19821201/CONUS_19821201_prism_ppt.tif',
    'symlink',
    '/vsizip/',
    '/prism/tiles/CONUS/19821201/PRISM_ppt_stable_4kmD2_19821201_bil.zip/PRISM_ppt_stable_4kmD2_19821201_bil.bil'),
   ('prism/tiles/CONUS/19821202/CONUS_19821202_prism_ppt.tif',
    'symlink',
    '/vsizip/',
    '/prism/tiles/CONUS/19821202/PRISM_ppt_stable_4kmD2_19821202_bil.zip/PRISM_ppt_stable_4kmD2_19821202_bil.bil'),
   ('prism/tiles/CONUS/19821203/CONUS_19821203_prism_ppt.tif',
    'symlink',
    '/vsizip/',
    '/prism/tiles/CONUS/19821203/PRISM_ppt_stable_4kmD2_19821203_bil.zip/PRISM_ppt_stable_4kmD2_19821203_bil.bil')]),

 # t_process[prism-pptsum] recording:
 ('pptsum',
  [('prism/tiles/CONUS/19821203/CONUS_19821203_prism_pptsum-3.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 1405, 621',
     'Coordinate System is:',
     'GEOGCS["NAD83",',
     '    DATUM["North_American_Datum_1983",',
     '        SPHEROID["GRS 1980",6378137,298.25722210,',
     '            AUTHORITY["EPSG","7019"]],',
     '        AUTHORITY["EPSG","6269"]],',
     '    PRIMEM["Greenwich",0],',
     '    UNIT["degree",0.01745329],',
     '    AUTHORITY["EPSG","4269"]]',
     'Origin = (-125.02083333,49.93750000)',
     'Pixel Size = (0.04166666,-0.04166666)',
     'Metadata:',
     '  AREA_OR_POINT=Area',
     '  GIPS_Prism_Version=0.1.1',
     '  GIPS_Source_Assets=PRISM_ppt_stable_4kmD2_19821201_bil.zip,PRISM_ppt_stable_4kmD2_19821202_bil.zip,PRISM_ppt_stable_4kmD2_19821203_bil.zip',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=BAND',
     'Corner Coordinates:',
     'Upper Left  (-125.0208333,  49.9375000) (125d 1\'15.00"W, 49d56\'15.00"N)',
     'Lower Left  (-125.0208333,  24.0625000) (125d 1\'15.00"W, 24d 3\'45.00"N)',
     'Upper Right ( -66.4791667,  49.9375000) ( 66d28\'45.00"W, 49d56\'15.00"N)',
     'Lower Right ( -66.4791667,  24.0625000) ( 66d28\'45.00"W, 24d 3\'45.00"N)',
     'Center      ( -95.7500000,  37.0000000) ( 95d45\' 0.00"W, 37d 0\' 0.00"N)',
     'Band 1 Block=1405x1 Type=Float32, ColorInterp=Gray',
     '  Description = Cumulative Precipitate(3 day window)',
     '  Minimum=-29997.000, Maximum=332.600, Mean=-13428.782, StdDev=14925.792',
     '  NoData Value=-9999',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=332.60000610',
     '    STATISTICS_MEAN=-13428.78234099',
     '    STATISTICS_MINIMUM=-29997',
     '    STATISTICS_STDDEV=14925.79199996'])]),
])


expectations['sar'] = collections.OrderedDict([
 # t_process[sar-date] recording:
 ('date',
  [('sar/tiles/N19E100/2010182/N19E100_2010182_AFBD_date.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 4500, 4500',
     'Coordinate System is:',
     'GEOGCS["WGS 84",',
     '    DATUM["WGS_1984",',
     '        SPHEROID["WGS 84",6378137,298.25722356,',
     '            AUTHORITY["EPSG","7030"]],',
     '        AUTHORITY["EPSG","6326"]],',
     '    PRIMEM["Greenwich",0],',
     '    UNIT["degree",0.01745329],',
     '    AUTHORITY["EPSG","4326"]]',
     'Origin = (100.00000000,19.00000000)',
     'Pixel Size = (0.00022227,-0.00022227)',
     'Metadata:',
     '  AREA_OR_POINT=Area',
     '  GIPS_Sar_Version=0.9.0',
     '  GIPS_Source_Assets=KC_017-Y10N19E100FBDORSA1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=BAND',
     'Corner Coordinates:',
     'Upper Left  ( 100.0000000,  19.0000000) (100d 0\' 0.00"E, 19d 0\' 0.00"N)',
     'Lower Left  ( 100.0000000,  17.9997777) (100d 0\' 0.00"E, 17d59\'59.20"N)',
     'Upper Right ( 101.0002223,  19.0000000) (101d 0\' 0.80"E, 19d 0\' 0.00"N)',
     'Lower Right ( 101.0002223,  17.9997777) (101d 0\' 0.80"E, 17d59\'59.20"N)',
     'Center      ( 100.5001111,  18.4998889) (100d30\' 0.40"E, 18d29\'59.60"N)',
     'Band 1 Block=4500x1 Type=UInt16, ColorInterp=Gray',
     '  Description = date',
     '  Minimum=0.000, Maximum=1728.000, Mean=1658.448, StdDev=37.451',
     '  NoData Value=-10000000000',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=1728',
     '    STATISTICS_MEAN=1658.44819728',
     '    STATISTICS_MINIMUM=0',
     '    STATISTICS_STDDEV=37.45119333']),
   ('sar/tiles/N00E099/2009041/N00E099_2009041_AWB1_date.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 1200, 1200',
     'Coordinate System is:',
     'GEOGCS["WGS 84",',
     '    DATUM["WGS_1984",',
     '        SPHEROID["WGS 84",6378137,298.25722356,',
     '            AUTHORITY["EPSG","7030"]],',
     '        AUTHORITY["EPSG","6326"]],',
     '    PRIMEM["Greenwich",0],',
     '    UNIT["degree",0.01745329],',
     '    AUTHORITY["EPSG","4326"]]',
     'Origin = (99.00000000,0.00000000)',
     'Pixel Size = (0.00083402,-0.00083402)',
     'Metadata:',
     '  AREA_OR_POINT=Area',
     '  GIPS_Sar_Version=0.9.0',
     '  GIPS_Source_Assets=KC_017-C25N00E099WB1ORSA1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=BAND',
     'Corner Coordinates:',
     'Upper Left  (  99.0000000,   0.0000000) ( 99d 0\' 0.00"E,  0d 0\' 0.01"N)',
     'Lower Left  (  99.0000000,  -1.0008340) ( 99d 0\' 0.00"E,  1d 0\' 3.00"S)',
     'Upper Right ( 100.0008340,   0.0000000) (100d 0\' 3.00"E,  0d 0\' 0.01"N)',
     'Lower Right ( 100.0008340,  -1.0008340) (100d 0\' 3.00"E,  1d 0\' 3.00"S)',
     'Center      (  99.5004170,  -0.5004170) ( 99d30\' 1.50"E,  0d30\' 1.50"S)',
     'Band 1 Block=1200x3 Type=UInt16, ColorInterp=Gray',
     '  Description = date',
     '  Minimum=1113.000, Maximum=1123.000, Mean=1116.856, StdDev=4.867',
     '  NoData Value=-10000000000',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=1123',
     '    STATISTICS_MEAN=1116.85558333',
     '    STATISTICS_MINIMUM=1113',
     '    STATISTICS_STDDEV=4.86726930']),
   ('sar/tiles/N07E099/2015101/N07E099_2015101_AWBD_date.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 2250, 2250',
     'Coordinate System is:',
     'GEOGCS["WGS 84",',
     '    DATUM["WGS_1984",',
     '        SPHEROID["WGS 84",6378137,298.25722356,',
     '            AUTHORITY["EPSG","7030"]],',
     '        AUTHORITY["EPSG","6326"]],',
     '    PRIMEM["Greenwich",0],',
     '    UNIT["degree",0.01745329],',
     '    AUTHORITY["EPSG","4326"]]',
     'Origin = (99.00000000,7.00000000)',
     'Pixel Size = (0.00044464,-0.00044464)',
     'Metadata:',
     '  AREA_OR_POINT=Area',
     '  GIPS_Sar_Version=0.9.0',
     '  GIPS_Source_Assets=KC_999-C019DRN07E099WBDORSA1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=BAND',
     'Corner Coordinates:',
     'Upper Left  (  99.0000000,   7.0000000) ( 99d 0\' 0.00"E,  7d 0\' 0.00"N)',
     'Lower Left  (  99.0000000,   5.9995554) ( 99d 0\' 0.00"E,  5d59\'58.40"N)',
     'Upper Right ( 100.0004446,   7.0000000) (100d 0\' 1.60"E,  7d 0\' 0.00"N)',
     'Lower Right ( 100.0004446,   5.9995554) (100d 0\' 1.60"E,  5d59\'58.40"N)',
     'Center      (  99.5002223,   6.4997777) ( 99d30\' 0.80"E,  6d29\'59.20"N)',
     'Band 1 Block=2250x1 Type=UInt16, ColorInterp=Gray',
     '  Description = date',
     '  Minimum=322.000, Maximum=322.000, Mean=322.000, StdDev=0.000',
     '  NoData Value=-10000000000',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=322',
     '    STATISTICS_MEAN=322',
     '    STATISTICS_MINIMUM=322',
     '    STATISTICS_STDDEV=0'])]),

 # t_process[sar-linci] recording:
 ('linci',
  [('sar/tiles/N19E100/2010182/N19E100_2010182_AFBD_linci.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 4500, 4500',
     'Coordinate System is:',
     'GEOGCS["WGS 84",',
     '    DATUM["WGS_1984",',
     '        SPHEROID["WGS 84",6378137,298.25722356,',
     '            AUTHORITY["EPSG","7030"]],',
     '        AUTHORITY["EPSG","6326"]],',
     '    PRIMEM["Greenwich",0],',
     '    UNIT["degree",0.01745329],',
     '    AUTHORITY["EPSG","4326"]]',
     'Origin = (100.00000000,19.00000000)',
     'Pixel Size = (0.00022227,-0.00022227)',
     'Metadata:',
     '  AREA_OR_POINT=Area',
     '  GIPS_Sar_Version=0.9.0',
     '  GIPS_Source_Assets=KC_017-Y10N19E100FBDORSA1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=BAND',
     'Corner Coordinates:',
     'Upper Left  ( 100.0000000,  19.0000000) (100d 0\' 0.00"E, 19d 0\' 0.00"N)',
     'Lower Left  ( 100.0000000,  17.9997777) (100d 0\' 0.00"E, 17d59\'59.20"N)',
     'Upper Right ( 101.0002223,  19.0000000) (101d 0\' 0.80"E, 19d 0\' 0.00"N)',
     'Lower Right ( 101.0002223,  17.9997777) (101d 0\' 0.80"E, 17d59\'59.20"N)',
     'Center      ( 100.5001111,  18.4998889) (100d30\' 0.40"E, 18d29\'59.60"N)',
     'Band 1 Block=4500x1 Type=Byte, ColorInterp=Gray',
     '  Description = linci',
     '  Minimum=0.000, Maximum=104.000, Mean=39.016, StdDev=11.171',
     '  NoData Value=-10000000000',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=104',
     '    STATISTICS_MEAN=39.01588409',
     '    STATISTICS_MINIMUM=0',
     '    STATISTICS_STDDEV=11.17138176']),
   ('sar/tiles/N00E099/2009041/N00E099_2009041_AWB1_linci.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 1200, 1200',
     'Coordinate System is:',
     'GEOGCS["WGS 84",',
     '    DATUM["WGS_1984",',
     '        SPHEROID["WGS 84",6378137,298.25722356,',
     '            AUTHORITY["EPSG","7030"]],',
     '        AUTHORITY["EPSG","6326"]],',
     '    PRIMEM["Greenwich",0],',
     '    UNIT["degree",0.01745329],',
     '    AUTHORITY["EPSG","4326"]]',
     'Origin = (99.00000000,0.00000000)',
     'Pixel Size = (0.00083402,-0.00083402)',
     'Metadata:',
     '  AREA_OR_POINT=Area',
     '  GIPS_Sar_Version=0.9.0',
     '  GIPS_Source_Assets=KC_017-C25N00E099WB1ORSA1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=BAND',
     'Corner Coordinates:',
     'Upper Left  (  99.0000000,   0.0000000) ( 99d 0\' 0.00"E,  0d 0\' 0.01"N)',
     'Lower Left  (  99.0000000,  -1.0008340) ( 99d 0\' 0.00"E,  1d 0\' 3.00"S)',
     'Upper Right ( 100.0008340,   0.0000000) (100d 0\' 3.00"E,  0d 0\' 0.01"N)',
     'Lower Right ( 100.0008340,  -1.0008340) (100d 0\' 3.00"E,  1d 0\' 3.00"S)',
     'Center      (  99.5004170,  -0.5004170) ( 99d30\' 1.50"E,  0d30\' 1.50"S)',
     'Band 1 Block=1200x6 Type=Byte, ColorInterp=Gray',
     '  Description = linci',
     '  Minimum=0.000, Maximum=83.000, Mean=31.460, StdDev=14.236',
     '  NoData Value=-10000000000',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=83',
     '    STATISTICS_MEAN=31.46008819',
     '    STATISTICS_MINIMUM=0',
     '    STATISTICS_STDDEV=14.23558432']),
   ('sar/tiles/N07E099/2015101/N07E099_2015101_AWBD_linci.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 2250, 2250',
     'Coordinate System is:',
     'GEOGCS["WGS 84",',
     '    DATUM["WGS_1984",',
     '        SPHEROID["WGS 84",6378137,298.25722356,',
     '            AUTHORITY["EPSG","7030"]],',
     '        AUTHORITY["EPSG","6326"]],',
     '    PRIMEM["Greenwich",0],',
     '    UNIT["degree",0.01745329],',
     '    AUTHORITY["EPSG","4326"]]',
     'Origin = (99.00000000,7.00000000)',
     'Pixel Size = (0.00044464,-0.00044464)',
     'Metadata:',
     '  AREA_OR_POINT=Area',
     '  GIPS_Sar_Version=0.9.0',
     '  GIPS_Source_Assets=KC_999-C019DRN07E099WBDORSA1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=BAND',
     'Corner Coordinates:',
     'Upper Left  (  99.0000000,   7.0000000) ( 99d 0\' 0.00"E,  7d 0\' 0.00"N)',
     'Lower Left  (  99.0000000,   5.9995554) ( 99d 0\' 0.00"E,  5d59\'58.40"N)',
     'Upper Right ( 100.0004446,   7.0000000) (100d 0\' 1.60"E,  7d 0\' 0.00"N)',
     'Lower Right ( 100.0004446,   5.9995554) (100d 0\' 1.60"E,  5d59\'58.40"N)',
     'Center      (  99.5002223,   6.4997777) ( 99d30\' 0.80"E,  6d29\'59.20"N)',
     'Band 1 Block=2250x3 Type=Byte, ColorInterp=Gray',
     '  Description = linci',
     '  Minimum=0.000, Maximum=115.000, Mean=36.142, StdDev=4.636',
     '  NoData Value=-10000000000',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=115',
     '    STATISTICS_MEAN=36.14166538',
     '    STATISTICS_MINIMUM=0',
     '    STATISTICS_STDDEV=4.63599063'])]),

 # t_process[sar-mask] recording:
 ('mask',
  [('sar/tiles/N07E099/2015101/N07E099_2015101_AWBD_mask.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 2250, 2250',
     'Coordinate System is:',
     'GEOGCS["WGS 84",',
     '    DATUM["WGS_1984",',
     '        SPHEROID["WGS 84",6378137,298.25722356,',
     '            AUTHORITY["EPSG","7030"]],',
     '        AUTHORITY["EPSG","6326"]],',
     '    PRIMEM["Greenwich",0],',
     '    UNIT["degree",0.01745329],',
     '    AUTHORITY["EPSG","4326"]]',
     'Origin = (99.00000000,7.00000000)',
     'Pixel Size = (0.00044464,-0.00044464)',
     'Metadata:',
     '  AREA_OR_POINT=Area',
     '  GIPS_Sar_Version=0.9.0',
     '  GIPS_Source_Assets=KC_999-C019DRN07E099WBDORSA1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=BAND',
     'Corner Coordinates:',
     'Upper Left  (  99.0000000,   7.0000000) ( 99d 0\' 0.00"E,  7d 0\' 0.00"N)',
     'Lower Left  (  99.0000000,   5.9995554) ( 99d 0\' 0.00"E,  5d59\'58.40"N)',
     'Upper Right ( 100.0004446,   7.0000000) (100d 0\' 1.60"E,  7d 0\' 0.00"N)',
     'Lower Right ( 100.0004446,   5.9995554) (100d 0\' 1.60"E,  5d59\'58.40"N)',
     'Center      (  99.5002223,   6.4997777) ( 99d30\' 0.80"E,  6d29\'59.20"N)',
     'Band 1 Block=2250x3 Type=Byte, ColorInterp=Gray',
     '  Description = mask',
     '  Minimum=50.000, Maximum=255.000, Mean=77.106, StdDev=69.232',
     '  NoData Value=0',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=255',
     '    STATISTICS_MEAN=77.10640790',
     '    STATISTICS_MINIMUM=50',
     '    STATISTICS_STDDEV=69.23210861']),
   ('sar/tiles/N19E100/2010182/N19E100_2010182_AFBD_mask.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 4500, 4500',
     'Coordinate System is:',
     'GEOGCS["WGS 84",',
     '    DATUM["WGS_1984",',
     '        SPHEROID["WGS 84",6378137,298.25722356,',
     '            AUTHORITY["EPSG","7030"]],',
     '        AUTHORITY["EPSG","6326"]],',
     '    PRIMEM["Greenwich",0],',
     '    UNIT["degree",0.01745329],',
     '    AUTHORITY["EPSG","4326"]]',
     'Origin = (100.00000000,19.00000000)',
     'Pixel Size = (0.00022227,-0.00022227)',
     'Metadata:',
     '  AREA_OR_POINT=Area',
     '  GIPS_Sar_Version=0.9.0',
     '  GIPS_Source_Assets=KC_017-Y10N19E100FBDORSA1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=BAND',
     'Corner Coordinates:',
     'Upper Left  ( 100.0000000,  19.0000000) (100d 0\' 0.00"E, 19d 0\' 0.00"N)',
     'Lower Left  ( 100.0000000,  17.9997777) (100d 0\' 0.00"E, 17d59\'59.20"N)',
     'Upper Right ( 101.0002223,  19.0000000) (101d 0\' 0.80"E, 19d 0\' 0.00"N)',
     'Lower Right ( 101.0002223,  17.9997777) (101d 0\' 0.80"E, 17d59\'59.20"N)',
     'Center      ( 100.5001111,  18.4998889) (100d30\' 0.40"E, 18d29\'59.60"N)',
     'Band 1 Block=4500x1 Type=Byte, ColorInterp=Gray',
     '  Description = mask',
     '  Minimum=100.000, Maximum=255.000, Mean=254.706, StdDev=6.732',
     '  NoData Value=0',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=255',
     '    STATISTICS_MEAN=254.70630637',
     '    STATISTICS_MINIMUM=100',
     '    STATISTICS_STDDEV=6.73232914']),
   ('sar/tiles/N00E099/2009041/N00E099_2009041_AWB1_mask.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 1200, 1200',
     'Coordinate System is:',
     'GEOGCS["WGS 84",',
     '    DATUM["WGS_1984",',
     '        SPHEROID["WGS 84",6378137,298.25722356,',
     '            AUTHORITY["EPSG","7030"]],',
     '        AUTHORITY["EPSG","6326"]],',
     '    PRIMEM["Greenwich",0],',
     '    UNIT["degree",0.01745329],',
     '    AUTHORITY["EPSG","4326"]]',
     'Origin = (99.00000000,0.00000000)',
     'Pixel Size = (0.00083402,-0.00083402)',
     'Metadata:',
     '  AREA_OR_POINT=Area',
     '  GIPS_Sar_Version=0.9.0',
     '  GIPS_Source_Assets=KC_017-C25N00E099WB1ORSA1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=BAND',
     'Corner Coordinates:',
     'Upper Left  (  99.0000000,   0.0000000) ( 99d 0\' 0.00"E,  0d 0\' 0.01"N)',
     'Lower Left  (  99.0000000,  -1.0008340) ( 99d 0\' 0.00"E,  1d 0\' 3.00"S)',
     'Upper Right ( 100.0008340,   0.0000000) (100d 0\' 3.00"E,  0d 0\' 0.01"N)',
     'Lower Right ( 100.0008340,  -1.0008340) (100d 0\' 3.00"E,  1d 0\' 3.00"S)',
     'Center      (  99.5004170,  -0.5004170) ( 99d30\' 1.50"E,  0d30\' 1.50"S)',
     'Band 1 Block=1200x6 Type=Byte, ColorInterp=Gray',
     '  Description = mask',
     '  Minimum=50.000, Maximum=255.000, Mean=66.968, StdDev=56.485',
     '  NoData Value=0',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=255',
     '    STATISTICS_MEAN=66.96823263',
     '    STATISTICS_MINIMUM=50',
     '    STATISTICS_STDDEV=56.48500693'])]),

 # t_process[sar-sign] recording:
 ('sign',
  [('sar/tiles/N00E099/2009041/N00E099_2009041_AWB1_sign.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 1200, 1200',
     'Coordinate System is:',
     'GEOGCS["WGS 84",',
     '    DATUM["WGS_1984",',
     '        SPHEROID["WGS 84",6378137,298.25722356,',
     '            AUTHORITY["EPSG","7030"]],',
     '        AUTHORITY["EPSG","6326"]],',
     '    PRIMEM["Greenwich",0],',
     '    UNIT["degree",0.01745329],',
     '    AUTHORITY["EPSG","4326"]]',
     'Origin = (99.00000000,0.00000000)',
     'Pixel Size = (0.00083402,-0.00083402)',
     'Metadata:',
     '  AREA_OR_POINT=Area',
     '  GIPS_Sar_Version=0.9.0',
     '  GIPS_Source_Assets=KC_017-C25N00E099WB1ORSA1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=BAND',
     'Corner Coordinates:',
     'Upper Left  (  99.0000000,   0.0000000) ( 99d 0\' 0.00"E,  0d 0\' 0.01"N)',
     'Lower Left  (  99.0000000,  -1.0008340) ( 99d 0\' 0.00"E,  1d 0\' 3.00"S)',
     'Upper Right ( 100.0008340,   0.0000000) (100d 0\' 3.00"E,  0d 0\' 0.01"N)',
     'Lower Right ( 100.0008340,  -1.0008340) (100d 0\' 3.00"E,  1d 0\' 3.00"S)',
     'Center      (  99.5004170,  -0.5004170) ( 99d30\' 1.50"E,  0d30\' 1.50"S)',
     'Band 1 Block=1200x1 Type=Float32, ColorInterp=Gray',
     '  Description = sl_HH',
     '  Minimum=-32.843, Maximum=12.641, Mean=-19.567, StdDev=6.280',
     '  NoData Value=-32768',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=12.64099216',
     '    STATISTICS_MEAN=-19.56703757',
     '    STATISTICS_MINIMUM=-32.84288406',
     '    STATISTICS_STDDEV=6.28044423']),
   ('sar/tiles/N07E099/2015101/N07E099_2015101_AWBD_sign.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 2250, 2250',
     'Coordinate System is:',
     'GEOGCS["WGS 84",',
     '    DATUM["WGS_1984",',
     '        SPHEROID["WGS 84",6378137,298.25722356,',
     '            AUTHORITY["EPSG","7030"]],',
     '        AUTHORITY["EPSG","6326"]],',
     '    PRIMEM["Greenwich",0],',
     '    UNIT["degree",0.01745329],',
     '    AUTHORITY["EPSG","4326"]]',
     'Origin = (99.00000000,7.00000000)',
     'Pixel Size = (0.00044464,-0.00044464)',
     'Metadata:',
     '  AREA_OR_POINT=Area',
     '  GIPS_Sar_Version=0.9.0',
     '  GIPS_Source_Assets=KC_999-C019DRN07E099WBDORSA1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=PIXEL',
     'Corner Coordinates:',
     'Upper Left  (  99.0000000,   7.0000000) ( 99d 0\' 0.00"E,  7d 0\' 0.00"N)',
     'Lower Left  (  99.0000000,   5.9995554) ( 99d 0\' 0.00"E,  5d59\'58.40"N)',
     'Upper Right ( 100.0004446,   7.0000000) (100d 0\' 1.60"E,  7d 0\' 0.00"N)',
     'Lower Right ( 100.0004446,   5.9995554) (100d 0\' 1.60"E,  5d59\'58.40"N)',
     'Center      (  99.5002223,   6.4997777) ( 99d30\' 0.80"E,  6d29\'59.20"N)',
     'Band 1 Block=2250x1 Type=Float32, ColorInterp=Gray',
     '  Description = sl_HV',
     '  Minimum=-51.636, Maximum=1.694, Mean=-31.702, StdDev=6.870',
     '  NoData Value=-32768',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=1.69439411',
     '    STATISTICS_MEAN=-31.70180599',
     '    STATISTICS_MINIMUM=-51.63596725',
     '    STATISTICS_STDDEV=6.87010582',
     'Band 2 Block=2250x1 Type=Float32, ColorInterp=Undefined',
     '  Description = sl_HH',
     '  Minimum=-36.765, Maximum=10.943, Mean=-20.779, StdDev=5.345',
     '  NoData Value=-32768',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=10.94336605',
     '    STATISTICS_MEAN=-20.77932701',
     '    STATISTICS_MINIMUM=-36.76492309',
     '    STATISTICS_STDDEV=5.34539689']),
   ('sar/tiles/N19E100/2010182/N19E100_2010182_AFBD_sign.tif',
    'raster',
    'gdalinfo-stats',
    ['Driver: GTiff/GeoTIFF',
     'Size is 4500, 4500',
     'Coordinate System is:',
     'GEOGCS["WGS 84",',
     '    DATUM["WGS_1984",',
     '        SPHEROID["WGS 84",6378137,298.25722356,',
     '            AUTHORITY["EPSG","7030"]],',
     '        AUTHORITY["EPSG","6326"]],',
     '    PRIMEM["Greenwich",0],',
     '    UNIT["degree",0.01745329],',
     '    AUTHORITY["EPSG","4326"]]',
     'Origin = (100.00000000,19.00000000)',
     'Pixel Size = (0.00022227,-0.00022227)',
     'Metadata:',
     '  AREA_OR_POINT=Area',
     '  GIPS_Sar_Version=0.9.0',
     '  GIPS_Source_Assets=KC_017-Y10N19E100FBDORSA1.tar.gz',
     '  GIPS_Version=0.0.0-dev',
     'Image Structure Metadata:',
     '  INTERLEAVE=PIXEL',
     'Corner Coordinates:',
     'Upper Left  ( 100.0000000,  19.0000000) (100d 0\' 0.00"E, 19d 0\' 0.00"N)',
     'Lower Left  ( 100.0000000,  17.9997777) (100d 0\' 0.00"E, 17d59\'59.20"N)',
     'Upper Right ( 101.0002223,  19.0000000) (101d 0\' 0.80"E, 19d 0\' 0.00"N)',
     'Lower Right ( 101.0002223,  17.9997777) (101d 0\' 0.80"E, 17d59\'59.20"N)',
     'Center      ( 100.5001111,  18.4998889) (100d30\' 0.40"E, 18d29\'59.60"N)',
     'Band 1 Block=4500x1 Type=Float32, ColorInterp=Gray',
     '  Description = sl_HV',
     '  Minimum=-32.193, Maximum=7.298, Mean=-13.801, StdDev=3.730',
     '  NoData Value=-32768',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=7.29838943',
     '    STATISTICS_MEAN=-13.80120513',
     '    STATISTICS_MINIMUM=-32.19340896',
     '    STATISTICS_STDDEV=3.72978558',
     'Band 2 Block=4500x1 Type=Float32, ColorInterp=Undefined',
     '  Description = sl_HH',
     '  Minimum=-32.577, Maximum=13.329, Mean=-7.783, StdDev=3.035',
     '  NoData Value=-32768',
     '  Metadata:',
     '    STATISTICS_MAXIMUM=13.32946586',
     '    STATISTICS_MEAN=-7.78253576',
     '    STATISTICS_MINIMUM=-32.57723999',
     '    STATISTICS_STDDEV=3.03543089'])]),
])
