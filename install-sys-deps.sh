#!/usr/bin/env bash

# Installs system packages needed for gips.  Should be run as root/sudo.
# Run via `source` or as its own process.

set -e -v

# installing gdal 2 via ubuntugis ppa:
apt-get update -y
apt-get install -y software-properties-common
add-apt-repository -y ppa:ubuntugis/ppa
apt-get update -y

# installing gips essentials:
# TODO not sure why need both curl & wget
# TODO installing system pip means pip can't upgrade itself without breaking
# TODO not clear if any of these are necessary; they were part of the gippy 0 + py2 installer:
#sudo apt-get install virtualenv libboost-all-dev libfreetype6-dev libgnutls-dev \
#   libatlas-base-dev python-numpy python-scipy swig2.0
# would be better to install python3-gdal via pypi package GDAL, but it causes conflicts
apt-get install -y \
    gdal-bin libgdal-dev python-dev python3-dev python3-gdal python3-pip \
    curl wget gfortran libgnutls28-dev