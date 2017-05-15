#!/bin/bash

# This script manages the deployment of the datahandler
# to a fresh linux container:
#
# if a container named $CONT doesn't exist, this:
#  + launches a fesh container named $CONT
#  + updates it
#  + installs some system package requirements
#  + snapshots it
# endif
# + restores the container to its `pipped` snapshot
# +
set -e
CONT=c1
{
    lxc info $CONT 2>&1>/dev/null || {
        time lxc launch ubuntu-daily:16.04 $CONT
        sleep 10
        lxc exec $CONT -- apt-get update
        sleep 10
        lxc exec $CONT -- apt-get install -y python python-apt python-pip
        # extra due to strange apt fetching issue
        lxc exec $CONT -- apt-get install -y gfortran libboost-all-dev libfreetype6-dev libgnutls-dev libatlas-base-dev libgdal-dev libgdal1-dev gdal-bin python-numpy python-scipy python-gdal swig2.0
        lxc exec $CONT -- pip install -U pip
    }
    echo "1"
    lxc info $CONT | grep Snapshots > /dev/null && echo "2" &&
        { echo "3" ; lxc restore $CONT pipped ; echo "4" ; } ||
            { echo "5" ; lxc snapshot $CONT pipped ; echo "6" ; }
    if $(lxc list $CONT | grep STOPPED) ; then
        lxc start $CONT
        sleep 1
    fi
}
lxc file push install_datahandler.py $CONT/root/
lxc exec $CONT -- python /root/install_datahandler.py \
    --drivers modis merra \
    --earthdata-user $EDUSER \
    --earthdata-password $EDPASS