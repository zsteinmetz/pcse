#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) 2004-2015 Alterra, Wageningen-UR
# Allard de Wit (allard.dewit@wur.nl)
# and Zacharias Steinmetz (stei4785@uni-landau.de), Aug 2015
"""
A weather data provider reading its data from CSV files.
"""
import os
import datetime as dt
import csv

from ..base_classes import WeatherDataContainer, WeatherDataProvider
from ..util import reference_ET, check_angstromAB
from ..exceptions import PCSEError
from ..settings import settings

# Conversion functions
NoConversion = lambda x: float(x)
MJ_to_J = lambda x: float(x)*1000000.
# kPa_to_hPa = lambda x: float(x)*10.
mm_to_cm = lambda x: float(x)/10.
csvdate_to_date = lambda x: dt.datetime.strptime(x, '%Y%m%d').date()


class IRSWeatherDataProvider(WeatherDataProvider):
    """Reading weather data from a CSV file as provided by CropM WP4 IRS2

    For further documentation see the CSVWeatherDataProvider module.
    """
    translator = {
        'DAY': ['w_date', 'DAY'],
        'IRRAD': ['srad', 'RADIATION'],
        'TMIN': ['tmin', 'TEMPERATURE_MIN'],
        'TMAX': ['tmax', 'TEMPERATURE_MAX'],
        'VAP': ['vprs_tx', 'VAPOURPRESSURE'],
        'WIND': ['wind', 'WINDSPEED'],
        'RAIN': ['rain', 'PRECIPITATION']
    }

    obs_conversions = {
        "TMAX": NoConversion,
        "TMIN": NoConversion,
        "IRRAD": MJ_to_J,
        "DAY": csvdate_to_date,
        "VAP": NoConversion,
        "WIND": NoConversion,
        "RAIN": mm_to_cm
    }

    def __init__(self, csv_fname, ETmodel='PM'):
        WeatherDataProvider.__init__(self)

        self.ETmodel = ETmodel
        self.fp_csv_fname = os.path.abspath(csv_fname)
        if not os.path.exists(self.fp_csv_fname):
            msg = "Cannot find weather file at: %s" % self.fp_csv_fname
            raise PCSEError(msg)

        if not self._load_cache_file(self.fp_csv_fname):    # Cache file cannot
                                                            # be loaded
            with open(csv_fname, newline='') as csv_file:
                site = csv_file.readline()[1:-1].split(' ')
                comment = csv_file.readline()[1:-1]
                obs = csv.reader(csv_file, delimiter=';', quotechar='"')

                self._read_meta(site, comment)
                self._read_observations(obs)
                self._write_cache_file(self.fp_csv_fname)

    def _read_meta(self, site, comment):

        country = site[0].split('/')[1]
        station = site[0].split('/')[0]
        desc = comment
        src = ''
        contact = ''
        self.nodata_value = -99
        self.description = [u"Weather data for:",
                            u"Country: %s" % country,
                            u"Station: %s" % station,
                            u"Description: %s" % desc,
                            u"Source: %s" % src,
                            u"Contact: %s" % contact]

        self.longitude = float(site[2].split('=')[1])
        self.latitude = float(site[1].split('=')[1])
        self.elevation = float(site[3].split('=')[1])
        angstA = -0.18
        angstB = -0.55
        self.angstA, self.angstB = check_angstromAB(angstA, angstB)

    def _read_observations(self, obs):

        # Start reading all rows with data
        _headerrow = True
        for row in obs:
            del row[-1]
            # Save header row.
            if _headerrow:
                header = row
                for (i, item) in enumerate(header):
                    header[i] = ''.join(key for key, value in
                        self.translator.items() if item in value)
                _headerrow = False
            else:
                d = dict(zip(header, row))
                if '' in d:
                    del d['']

                for h in d.keys():
                    func = self.obs_conversions[h]
                    d[h] = func(d[h])

                # Reference ET in mm/day
                e0, es0, et0 = reference_ET(LAT=self.latitude,
                                            ELEV=self.elevation,
                                            ANGSTA=self.angstA,
                                            ANGSTB=self.angstB, **d)
                # convert to cm/day
                d["E0"] = e0/10.
                d["ES0"] = es0/10.
                d["ET0"] = et0/10.

                wdc = WeatherDataContainer(LAT=self.latitude,
                                           LON=self.longitude,
                                           ELEV=self.elevation, **d)
                self._store_WeatherDataContainer(wdc, d["DAY"])

    def _load_cache_file(self, csv_fname):

        cache_filename = self._find_cache_file(csv_fname)
        if cache_filename is None:
            return False
        else:
            self._load(cache_filename)
            return True

    def _find_cache_file(self, csv_fname):
        """Try to find a cache file for file name

        Returns None if the cache file does not exist, else it returns the full
        path to the cache file.
        """
        cache_filename = self._get_cache_filename(csv_fname)
        if os.path.exists(cache_filename):
            cache_date = os.stat(cache_filename).st_mtime
            csv_date = os.stat(csv_fname).st_mtime
            if cache_date > csv_date:  # cache is more recent then XLS file
                return cache_filename

        return None

    def _get_cache_filename(self, csv_fname):
        """Constructs the filename used for cache files given csv_fname
        """
        basename = os.path.basename(csv_fname)
        filename, ext = os.path.splitext(basename)

        tmp = "%s_%s.cache" % (self.__class__.__name__, filename)
        cache_filename = os.path.join(settings.METEO_CACHE_DIR, tmp)
        return cache_filename

    def _write_cache_file(self, csv_fname):

        cache_filename = self._get_cache_filename(csv_fname)
        try:
            self._dump(cache_filename)
        except (IOError, EnvironmentError) as e:
            msg = "Failed to write cache to file '%s' due to: %s" % (cache_filename, e)
            self.logger.warning(msg)
