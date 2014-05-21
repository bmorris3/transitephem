transitephem
============

A Pythonic transiting exoplanet ephemeris generator by [Brett Morris (UW)](http://staff.washington.edu/bmmorris/). Requirements include Numpy, PyEphem, and astropy. These scripts are largely lifted from [OSCAAR](http://oscaar.github.io/OSCAAR/), and make use of exoplanet data from [exoplanets.org](http://exoplanets.org/). 

The transit time predictions are likely accurate to within an hour -- those transit events with the oldest references likely have the most inaccurate transit time predictions.

To run transitephem, clone this repository, change directories into it, edit the `mro.par` file which contains your observing parameters, and execute the script with 
```
$ python transitephem.py
```

Parameters
----------
The observatory parameters are logged in `mro.par`, and have the following keywords and value formats:
* `name`: string, name of the observatory
* `latitude`: observatory latitude; format = deg:min:sec
* `longitude`: observatory longitude; format = deg:min:sec
* `elevation`: observatory elevation in meters
* `temperature`: air temperature in degrees C
* `min_horizon`: the pointing limit of your telescope in degrees above the horizon; format = deg:min:sec
* `start_date`: start time in UT of the ephemeris; format = (YYYY,MM,DD,HH,MM,SS)
* `end_date`: end time in UT of the ephemeris; format = (YYYY,MM,DD,HH,MM,SS)
* `mag_limit`: the magnitude of the faintest exoplanet host star that you would like listed in the ephemeris
* `depth_limit`: the lower limit on the depth of transit that you would like listed in the ephemeris, in units of millimag
* `calc_transits`: calculate ephemeris for transit events; format = boolean
* `calc_eclipses`: calculate ephemeris for secondary eclipse events; format = boolean
* `html_out`: save HTML output; format = boolean
* `text_out`: save CSV output; format = boolean
* `twilight`: altitude of the sun in degrees at "twilight", i.e. [civil (-6), nautical (-12) or astronomical (-18) twilight](http://en.wikipedia.org/wiki/Twilight#Definitions); format = float (default = -6)
* `band`: default observing band (used for selection by the `mag_limit` keyword); options = V or K
