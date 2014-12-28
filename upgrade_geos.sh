#!/bin/sh
wget http://download.osgeo.org/geos/geos-3.4.2.tar.bz2
tar xjvf geos-3.4.2.tar.bz2
cd geos-3.4.2
./configure --prefix=/usr
make
make install