'''
Ephemeris calculating tool that uses transit data from exoplanets.org
and astrometric calculations by PyEphem to tell you what transits you'll
be able to observe from your observatory in the near future.

Exoplanets.org citation: Wright et al.2011
http://arxiv.org/pdf/1012.5676v3.pdf

Core developer: Brett Morris
'''
import ephem	 ## PyEphem module
import numpy as np
from glob import glob
import time
from astropy.time import Time
import os.path
import cPickle
import sys
from urllib import urlopen
import re

rootdir = './outputs/'
exodbPath = './outputs/'#rootdir+'exodb'

def gd2jd(gdlist):
    '''
    Parameters
    ----------
    gdlist : list
        Gregorian date in list format - [year,month,day,hour,minute,second]
    Returns
    -------
    jd : float
        Julian date
    '''
    
    # Convert the input list into a string in "ISO" format for astropy
    gdstring = "%i-%i-%i %s:%s:%s" % tuple(gdlist)
    return Time(gdstring, format='iso', scale='utc').jd

def jd2gd(jd):
    '''
    Parameters
    ----------
    jd : float
        Time in julian date
    Returns
    -------
    gdlist : list
        Gregorian date in list format - [year,month,day,hour,minute,second]
    '''
    string = Time(jd, format='jd', scale='utc').iso
    return tuple(map(int,re.findall(r"[\w']+",string)[:-1]))


def downloadAndPickle():
    pklDatabaseName = os.path.join(exodbPath,'exoplanetDB.pkl')	 ## Name of exoplanet database C-pickle
    pklDatabasePaths = glob(pklDatabaseName)   ## list of files with the name pklDatabaseName in cwd
    csvDatabaseName = os.path.join(exodbPath,'exoplanets.csv')  ## Path to the text file saved from exoplanets.org
    csvDatabasePaths = glob(csvDatabaseName)

    '''First, check if there is an internet connection.'''

    '''If there's a previously archived database pickle in this current working 
        directory then use it, if not, grab the data from exoplanets.org in one big CSV file and make one.
        If the old archive is >14 days old, grab a fresh version of the database from exoplanets.org.
        '''
    if csvDatabasePaths == []:
        print 'No local copy of exoplanets.org database. Downloading one...'
        rawCSV = urlopen('http://www.exoplanets.org/csv-files/exoplanets.csv').read()
        saveCSV = open(csvDatabaseName,'w')
        saveCSV.write(rawCSV)
        saveCSV.close()
    else: 
        '''If the local copy of the exoplanets.org database is >14 days old, download a new one'''
        secondsSinceLastModification = time.time() - os.path.getmtime(csvDatabaseName) ## in seconds
        daysSinceLastModification = secondsSinceLastModification/(60*60*24*30)
        if daysSinceLastModification > 7:
            print 'Your local copy of the exoplanets.org database is >14 days old. Downloading a fresh one...'
            rawCSV = urlopen('http://www.exoplanets.org/csv-files/exoplanets.csv').read()
            saveCSV = open(csvDatabaseName,'w')
            saveCSV.write(rawCSV)
            saveCSV.close()
        else: print "Your local copy of the exoplanets.org database is <14 days old. That'll do."

    if len(pklDatabasePaths) == 0:
        print 'Parsing '+os.path.split(csvDatabaseName)[1]+', the CSV database from exoplanets.org...'
        rawTable = open(csvDatabaseName).read().splitlines()
        labels = rawTable[0].split(',')
        #labelUnits = rawTable[1].split(',')
        #rawTableArray = np.zeros([len(rawTable),len(labels)])
        exoplanetDB = {}
        planetNameColumn = np.arange(len(labels))[np.array(labels,dtype=str)=='NAME'][0]
        for row in range(1,len(rawTable)): 
            splitRow = rawTable[row].split(',')
            exoplanetDB[splitRow[planetNameColumn]] = {}	## Create dictionary for this row's planet
            for col in range(0,len(splitRow)):
                exoplanetDB[splitRow[planetNameColumn]][labels[col]] = splitRow[col]
        
        output = open(pklDatabaseName,'wb')
        cPickle.dump(exoplanetDB,output)
        output.close()
    else: 
        print 'Using previously parsed database from exoplanets.org...'
        inputFile = open(pklDatabaseName,'rb')
        exoplanetDB = cPickle.load(inputFile)
        inputFile.close()
    
    return exoplanetDB

def calculateEphemerides(parFile):
    '''
        :INPUTS:
        parFile	 --	  path to the parameter file
        '''


    '''Parse the observatory .par file'''
    parFileText = open(os.path.join(os.path.dirname(__file__),parFile),'r').read().splitlines()

    def returnBool(value):
        '''Return booleans from strings'''
        if value.upper().strip() == 'TRUE': return True
        elif value.upper().strip() == 'FALSE': return False
    if hasattr(sys, 'real_prefix'):
        show_lt = float(0)
    for line in parFileText:
        parameter = line.split(':')[0]
        if len(line.split(':')) > 1:
            value = line.split(':')[1].strip()
            if parameter == 'name': observatory_name = value
            elif parameter == 'latitude': observatory_latitude = value
            elif parameter == 'longitude': observatory_longitude = value
            elif parameter == 'elevation': observatory_elevation = float(value)
            elif parameter == 'temperature': observatory_temperature = float(value)
            elif parameter == 'min_horizon': observatory_minHorizon = value
            elif parameter == 'start_date': startSem = gd2jd(eval(value))
            elif parameter == 'end_date': endSem = gd2jd(eval(value))
            elif parameter == 'mag_limit': mag_limit = float(value)
            elif parameter == 'band': band = value
            elif parameter == 'depth_limit': depth_limit = float(value)
            elif parameter == 'calc_transits': calcTransits = returnBool(value)
            elif parameter == 'calc_eclipses': calcEclipses = returnBool(value)
            elif parameter == 'html_out': htmlOut = returnBool(value)
            elif parameter == 'text_out': textOut = returnBool(value)
            elif parameter == 'twilight': twilightType = value
            elif parameter == 'show_lt': show_lt = float(value)
    #from oscaar.extras.knownSystemParameters import getLatestParams
    exoplanetDB = downloadAndPickle()

    ''' Set up observatory parameters '''
    observatory = ephem.Observer()
    observatory.lat =  observatory_latitude#'38:58:50.16'	## Input format-  deg:min:sec  (type=str)
    observatory.long = observatory_longitude#'-76:56:13.92' ## Input format-  deg:min:sec  (type=str)
    observatory.elevation = observatory_elevation   # m
    observatory.temp = observatory_temperature	  ## Celsius 
    observatory.horizon = observatory_minHorizon	## Input format-  deg:min:sec  (type=str)

    def trunc(f, n):
        '''Truncates a float f to n decimal places without rounding'''
        slen = len('%.*f' % (n, f))
        return str(f)[:slen]

    def RA(planet):
        '''Type: str, Units:  hours:min:sec'''
        return exoplanetDB[planet]['RA_STRING']
    def dec(planet):
        '''Type: str, Units:  deg:min:sec'''
        return exoplanetDB[planet]['DEC_STRING']
    def period(planet):
        '''Units:  days'''
        return np.float64(exoplanetDB[planet]['PER'])
    def epoch(planet):
        '''Tc at mid-transit. Units:  days'''
        if exoplanetDB[planet]['TT'] == '': return 0.0
        else: return np.float64(exoplanetDB[planet]['TT'])
    def duration(planet):
        '''Transit/eclipse duration. Units:  days'''
        if exoplanetDB[planet]['T14'] == '': return 0.0
        else: return float(exoplanetDB[planet]['T14'])
    def V(planet):
        '''V mag'''
        if exoplanetDB[planet]['V'] == '': return 0.0
        else: return float(exoplanetDB[planet]['V'])
    def KS(planet):
        '''KS mag'''
        if exoplanetDB[planet]['KS'] == '': return 0.0
        else: return float(exoplanetDB[planet]['KS'])
    
    def bandMagnitude(planet):
        if band.upper() == 'V':
            return V(planet)
        elif band.upper() == 'K':
            return KS(planet)
    def depth(planet):
        '''Transit depth'''
        if exoplanetDB[planet]['DEPTH'] == '': return 0.0
        else: return float(exoplanetDB[planet]['DEPTH'])

    def transitBool(planet):
        '''True if exoplanet is transiting, False if detected by other means'''
        if exoplanetDB[planet]['TRANSIT'] == '0': return 0
        elif exoplanetDB[planet]['TRANSIT'] == '1': return 1
    ########################################################################################
    ########################################################################################

    def datestr2list(datestr):
        ''' Take strings of the form: "2013/1/18 20:08:18" and return them as a
            tuple of the same parameters'''
        year,month,others = datestr.split('/')
        day, time = others.split(' ')
        hour,minute,sec = time.split(':')
        return (int(year),int(month),int(day),int(hour),int(minute),int(sec))

    def list2datestr(inList):
        '''Converse function to datestr2list'''
        inList = map(str,inList)
        return inList[0]+'/'+inList[1]+'/'+inList[2]+' '+inList[3].zfill(2)+':'+inList[4].zfill(2)+':'+inList[5].zfill(2)

    def list2datestrCSV(inList):
        '''Converse function to datestr2list'''
        inList = map(str,inList)
        #print inList
        return inList[0]+'/'+inList[1]+'/'+inList[2]+','+inList[3].zfill(2)+':'+inList[4].zfill(2)+':'+inList[5].zfill(2)


    def list2datestrHTML(inList,alt,direction):
        '''Converse function to datestr2list'''
        inList = map(str,inList)
        #return inList[1].zfill(2)+'/'+inList[2].zfill(2)+'<br />'+inList[3].zfill(2)+':'+inList[4].zfill(2)
        return inList[1].zfill(2)+'/<strong>'+inList[2].zfill(2)+'</strong>, '+inList[3].zfill(2)+':'+inList[4].split('.')[0].zfill(2)+'<br /> '+alt+'&deg; '+direction

    def list2datestrHTML_UTnoaltdir(inList,alt,direction):
        '''Converse function to datestr2list'''
        inList = map(str,inList)
        #return inList[1].zfill(2)+'/'+inList[2].zfill(2)+'<br />'+inList[3].zfill(2)+':'+inList[4].zfill(2)
        return inList[1].zfill(2)+'/<strong>'+inList[2].zfill(2)+'</strong>, '+inList[3].zfill(2)+':'+inList[4].split('.')[0].zfill(2)

    def list2datestrHTML_LT(inList,alt,direction):
        '''Converse function to datestr2list for daylight savings time'''
        #print "original",inList
        tempDate = ephem.Date(inList)
        inList = ephem.Date(ephem.localtime(tempDate)).tuple()
        #print "converted",lt_inList,'\n'
        inList = map(str,inList)
        #return inList[1].zfill(2)+'/'+inList[2].zfill(2)+'<br />'+inList[3].zfill(2)+':'+inList[4].zfill(2)
        return inList[1].zfill(2)+'/<strong>'+inList[2].zfill(2)+'</strong>, '+inList[3].zfill(2)+':'+inList[4].split('.')[0].zfill(2)+'<br /> '+alt+'&deg; '+direction

    def simbadURL(planet):
        if exoplanetDB[planet]['SIMBADURL'] == '': return 'http://simbad.harvard.edu/simbad/'
        else: return exoplanetDB[planet]['SIMBADURL']

    def RADecHTML(planet):
        return '<a href="'+simbadURL(planet)+'">'+RA(planet).split('.')[0]+'<br />'+dec(planet).split('.')[0]+'</a>'

    def constellation(planet):
        return exoplanetDB[planet]['Constellation']

    def orbitReference(planet):
        return exoplanetDB[planet]['TRANSITURL']

    def orbitReferenceYear(planet):
        '''ORBREF returns the citation in the format "<first author> <year>", so parse and return just the year'''
        return exoplanetDB[planet]['ORBREF'].split()[1]

    def nameWithLink(planet):
        return '<a href="'+orbitReference(planet)+'">'+planet+'</a>'

    def mass(planet):
        if exoplanetDB[planet]['MASS'] == '': return '---'
        else: return trunc(float(exoplanetDB[planet]['MASS']),2)

    def semimajorAxis(planet):
        #return trunc(0.004649*float(exoplanetDB[planet]['AR'])*float(exoplanetDB[planet]['RSTAR']),3)   ## Convert from solar radii to AU
        return trunc(float(exoplanetDB[planet]['SEP']),3)

    def radius(planet):
        if exoplanetDB[planet]['R'] == '': return '---'
        else: return trunc(float(exoplanetDB[planet]['R']),2) ## Convert from solar radii to Jupiter radii

    def midTransit(Tc, P, start, end):
        '''Calculate mid-transits between Julian Dates start and end, using a 2500 
            orbital phase kernel since T_c (for 2 day period, 2500 phases is 14 years)
            '''
        Nepochs = np.arange(0,2500,dtype=np.float64)
        transitTimes = Tc + P*Nepochs
        transitTimesInSem = transitTimes[(transitTimes < end)*(transitTimes > start)]
        return transitTimesInSem

    def midEclipse(Tc, P, start, end):
        '''Calculate mid-eclipses between Julian Dates start and end, using a 2500 
            orbital phase kernel since T_c (for 2 day period, 2500 phases is 14 years)
            '''
        Nepochs = np.arange(0,2500,dtype=np.float64)
        transitTimes = Tc + P*(0.5 + Nepochs)
        transitTimesInSem = transitTimes[(transitTimes < end)*(transitTimes > start)]
        return transitTimesInSem

    '''Choose which planets from the database to include in the search, 
        assemble a list of them.'''
    planets = []
    for planet in exoplanetDB:
        if bandMagnitude(planet) != 0.0 and depth(planet) != 0.0 and float(bandMagnitude(planet)) <= mag_limit and \
           float(depth(planet)) >= depth_limit and transitBool(planet):
            planets.append(planet)

    if calcTransits: transits = {}
    if calcEclipses: eclipses = {}
    for day in np.arange(startSem,endSem+1):
        if calcTransits: transits[str(day)] = []
        if calcEclipses: eclipses[str(day)] = []
    planetsNeverUp = []


    def azToDirection(az):
        az = float(az)
        if (az >= 0 and az < 22.5) or (az >= 337.5 and az < 360): return 'N'
        elif az >= 22.5 and az < 67.5:  return 'NE'
        elif az >= 67.5 and az < 112.5:  return 'E'
        elif az >= 112.5 and az < 157.5:  return 'SE'
        elif az >= 157.5 and az < 202.5:  return 'S'
        elif az >= 202.5 and az < 247.5:  return 'SW'
        elif az >= 247.5 and az < 292.5:  return 'W'	
        elif az >= 292.5 and az < 337.5:  return 'NW'

    def ingressEgressAltAz(planet,observatory,ingress,egress):
        altitudes = []
        directions = []
        for time in [ingress,egress]:
            observatory.date = list2datestr(jd2gd(time))
            star = ephem.FixedBody()
            star._ra = ephem.hours(RA(planet))
            star._dec = ephem.degrees(dec(planet))
            star.compute(observatory)
            altitudes.append(str(ephem.degrees(star.alt)).split(":")[0])
            directions.append(azToDirection(str(ephem.degrees(star.az)).split(":")[0]))
        ingressAlt,egressAlt = altitudes
        ingressDir,egressDir = directions
        return ingressAlt,ingressDir,egressAlt,egressDir

    def aboveHorizonForEvent(planet,observatory,ingress,egress):
        altitudes = []
        for time in [ingress,egress]:
            observatory.date = list2datestr(jd2gd(time))
            star = ephem.FixedBody()
            star._ra = ephem.hours(RA(planet))
            star._dec = ephem.degrees(dec(planet))
            star.compute(observatory)
            #altitudes.append(str(ephem.degrees(star.alt)).split(":")[0])
            altitudes.append(float(repr(star.alt))/(2*np.pi) * 360)	## Convert altitudes to degrees
        #if altitudes[0] > 0 and altitudes[1] > 0: return True
        if altitudes[0] > float(ephem.degrees(observatory_minHorizon))*(180/np.pi) and altitudes[1] > float(ephem.degrees(observatory_minHorizon))*(180/np.pi): return True
        else: return False

    def eventAfterTwilight(planet,observatory,ingress,egress,twilightType):
        altitudes = []
        for time in [ingress,egress]:
            observatory.date = list2datestr(jd2gd(time))
            sun = ephem.Sun()
            sun.compute(observatory)
            altitudes.append(float(repr(sun.alt))/(2*np.pi) * 360)	## Convert altitudes to degrees
        if altitudes[0] < float(twilightType) and altitudes[1] < float(twilightType): return True
        else: return False

    for planet in planets:		
        '''Compute all of the coming transits and eclipses for a long time out'''
        allTransitEpochs = midTransit(epoch(planet),period(planet),startSem,endSem)
        allEclipseEpochs = midEclipse(epoch(planet),period(planet),startSem,endSem)
        for day in np.arange(startSem,endSem+1,1.0):
            try:
                '''For each day, gather the transits and eclipses that happen'''
                transitEpochs = allTransitEpochs[(allTransitEpochs <= day+0.5)*(allTransitEpochs > day-0.5)]
                eclipseEpochs = allEclipseEpochs[(allEclipseEpochs <= day+0.5)*(allEclipseEpochs > day-0.5)]
                if calcTransits and len(transitEpochs) != 0:
                    transitEpoch = transitEpochs[0]
                    ingress = transitEpoch-duration(planet)/2
                    egress = transitEpoch+duration(planet)/2
                    
                    ''' Calculate positions of host stars'''
                    star = ephem.FixedBody()
                    star._ra = ephem.hours(RA(planet))
                    star._dec = ephem.degrees(dec(planet))
                    star.compute(observatory)
                    exoplanetDB[planet]['Constellation'] = ephem.constellation(star)[0]
                    
                    '''If star is above horizon and sun is below horizon during transit/eclipse:'''		
                    if aboveHorizonForEvent(planet,observatory,ingress,egress) and eventAfterTwilight(planet,observatory,ingress,egress,twilightType):
                        ingressAlt,ingressDir,egressAlt,egressDir = ingressEgressAltAz(planet,observatory,ingress,egress)
                        transitInfo = [planet,transitEpoch,duration(planet)/2,'transit',ingressAlt,ingressDir,egressAlt,egressDir]
                        transits[str(day)].append(transitInfo)		
                if calcEclipses and len(eclipseEpochs) != 0:
                    eclipseEpoch = eclipseEpochs[0]
                    ingress = eclipseEpoch-duration(planet)/2
                    egress = eclipseEpoch+duration(planet)/2
                    
                    ''' Calculate positions of host stars'''
                    star = ephem.FixedBody()
                    star._ra = ephem.hours(RA(planet))
                    star._dec = ephem.degrees(dec(planet))
                    star.compute(observatory)
                    exoplanetDB[planet]['Constellation'] = ephem.constellation(star)[0]
                    
                    if aboveHorizonForEvent(planet,observatory,ingress,egress) and eventAfterTwilight(planet,observatory,ingress,egress,twilightType):
                        ingressAlt,ingressDir,egressAlt,egressDir = ingressEgressAltAz(planet,observatory,ingress,egress)
                        eclipseInfo = [planet,eclipseEpoch,duration(planet)/2,'eclipse',ingressAlt,ingressDir,egressAlt,egressDir]
                        eclipses[str(day)].append(eclipseInfo)	
            
            except ephem.NeverUpError:
                if str(planet) not in planetsNeverUp:
                    print 'Note: planet %s is never above the horizon at this observing location.' % (planet)
                    planetsNeverUp.append(str(planet))

    def removeEmptySets(dictionary):
        '''Remove days where there were no transits/eclipses from the transit/eclipse list dictionary. 
            Can't iterate through the transits dictionary with a for loop because it would change length 
            as keys get deleted, so loop through with while loop until all entries are not empty sets'''
        dayCounter = startSem
        while any(dictionary[day] == [] for day in dictionary):	
            if dictionary[str(dayCounter)] == []:
                del dictionary[str(dayCounter)]
            dayCounter += 1

    if calcTransits: removeEmptySets(transits)
    if calcEclipses: removeEmptySets(eclipses)

    events = {}
    def mergeDictionaries(dict):
        for key in dict:
            if any(key == eventKey for eventKey in events) == False:	## If key does not exist in events,
                if np.shape(dict[key])[0] == 1:	## If new event is the only one on that night, add only it
                    events[key] = [dict[key][0]]
                else:			## If there were multiple events that night, add them each
                    events[key] = []
                    for event in dict[key]:
                        events[key].append(event)
            else:
                if np.shape(dict[key])[0] > 1: ## If there are multiple entries to append,
                    for event in dict[key]:
                        events[key].append(event)
                else:							## If there is only one to add,
                    events[key].append(dict[key][0])
    if calcTransits: mergeDictionaries(transits)
    if calcEclipses: mergeDictionaries(eclipses)

    if textOut: 
        allKeys = events.keys()
        allKeys = np.array(allKeys)[np.argsort(allKeys)]
        #report = open(os.path.join(os.path.dirname(oscaar.__file__),'extras','eph','ephOutputs','eventReport.csv'),'w')
        report = open(os.path.join(os.path.abspath(rootdir),'eventReport.csv'),'w')
        firstLine = 'Planet,Event,Ingress Date, Ingress Time (UT) ,Altitude at Ingress,Azimuth at Ingress,Egress Date, Egress Time (UT) ,Altitude at Egress,Azimuth at Egress,V mag,Depth,Duration,RA,Dec,Const.,Mass,Semimajor Axis (AU),Radius (R_J)\n'
        report.write(firstLine)
        
        for key in allKeys:
            def writeCSVtransit():
                middle = ','.join([planet[0],str(planet[3]),list2datestrCSV(jd2gd(float(planet[1]-planet[2]))),planet[4],planet[5],\
                                   list2datestrCSV(jd2gd(float(planet[1]+planet[2]))),planet[6],planet[7],trunc(bandMagnitude(str(planet[0])),2),\
                                   trunc(depth(planet[0]),4),trunc(24.0*duration(planet[0]),2),RA(planet[0]),dec(planet[0]),constellation(planet[0]),\
                                   mass(planet[0]),semimajorAxis(planet[0]),radius(planet[0])])
                line = middle+'\n'
                report.write(line)
            
            def writeCSVeclipse():
                middle = ','.join([planet[0],str(planet[3]),list2datestrCSV(jd2gd(float(planet[1]-planet[2]))),planet[4],planet[5],\
                                   list2datestrCSV(jd2gd(float(planet[1]+planet[2]))),planet[6],planet[7],trunc(bandMagnitude(str(planet[0])),2),\
                                   trunc(depth(planet[0]),4),trunc(24.0*duration(planet[0]),2),RA(planet[0]),dec(planet[0]),constellation(planet[0]),\
                                   mass(planet[0]),semimajorAxis(planet[0]),radius(planet[0])])
                line = middle+'\n'
                report.write(line)
            
            if np.shape(events[key])[0] > 1:
                elapsedTime = []
                
                for i in range(1,len(events[key])):
                    nextPlanet = events[key][1]
                    planet = events[key][0]
                    double = False
                    '''If the other planet's ingress is before this one's egress, then'''
                    if ephem.Date(list2datestr(jd2gd(float(nextPlanet[1]-nextPlanet[2])))) -\
                        ephem.Date(list2datestr(jd2gd(float(planet[1]+planet[2])))) > 0.0:
                            double = True
                            elapsedTime.append(ephem.Date(list2datestr(jd2gd(float(nextPlanet[1]-nextPlanet[2])))) - \
                                               ephem.Date(list2datestr(jd2gd(float(planet[1]+planet[2])))))
                    
                    if ephem.Date(list2datestr(jd2gd(float(planet[1]-planet[2])))) - \
                        ephem.Date(list2datestr(jd2gd(float(nextPlanet[1]+nextPlanet[2])))) > 0.0:
                            '''If the other planet's egress is before this one's ingress, then'''
                            double = True
                            elapsedTime.append(ephem.Date(list2datestr(jd2gd(float(planet[1]-planet[2])))) - \
                                               ephem.Date(list2datestr(jd2gd(float(nextPlanet[1]+nextPlanet[2])))))
                
                for planet in events[key]:
                    if calcTransits and planet[3] == 'transit':
                        writeCSVtransit()
                    if calcEclipses and planet[3] == 'eclipse':
                        writeCSVeclipse()		  
            
            elif np.shape(events[key])[0] == 1:
                planet = events[key][0]
                if calcTransits and planet[3] == 'transit':
                    writeCSVtransit()
                if calcEclipses and planet[3] == 'eclipse':
                    writeCSVeclipse()
        # report.write('\n')
        
        report.close()
    #print exoplanetDB['HD 209458 b']
    print 'calculateEphemerides.py: Done'


    if htmlOut: 
        '''Write out a text report with the transits/eclipses. Write out the time of 
            ingress, egress, whether event is transit/eclipse, elapsed in time between
            ingress/egress of the temporally isolated events'''
        report = open(os.path.join(os.path.abspath(rootdir),'eventReport.html'),'w')
        allKeys = events.keys()
        ## http://www.kryogenix.org/code/browser/sorttable/
        htmlheader = '\n'.join([
                                '<!doctype html>',\
                                '<html>',\
                                '	<head>',\
                                '		<meta http-equiv="content-type" content="text/html; charset=UTF-8" />',\
                                '		<title>Ephemeris</title>',\
                                '		<link rel="stylesheet" href="stylesheetEphem.css" type="text/css" />',\
                                '		 <script type="text/javascript">',\
                                '		  function changeCSS(cssFile, cssLinkIndex) {',\
                                '			var oldlink = document.getElementsByTagName("link").item(cssLinkIndex);',\
                                '			var newlink = document.createElement("link")',\
                                '			newlink.setAttribute("rel", "stylesheet");',\
                                '			newlink.setAttribute("type", "text/css");',\
                                '			newlink.setAttribute("href", cssFile);',\
                                
                                '			document.getElementsByTagName("head").item(0).replaceChild(newlink, oldlink);',\
                                '		  }',\
                                '		</script>',\
                                '	   <script src="./sorttable.js"></script>',\
                                '	</head>',\
                                '	<body>',\
                                '		<div id="textDiv">',\
                                '		<h1>Ephemerides for: '+observatory_name+'</h1>',\
                                '		<h2>Observing dates (UT): '+list2datestr(jd2gd(startSem)).split(' ')[0]+' - '+list2datestr(jd2gd(endSem)).split(' ')[0]+'</h2>'
                                '	   Click the column headers to sort. ',\
                                '		<table class="daynight" id="eph">',\
                                '		<tr><th colspan=2>Toggle Color Scheme</th></tr>',\
                                '		<tr><td><a href="#" onclick="changeCSS(\'stylesheetEphem.css\', 0);">Day</a></td><td><a href="#" onclick="changeCSS(\'stylesheetEphemDark.css\', 0);">Night</a></td></tr>',\
                                '		</table>'])
        
        if show_lt == 0:
            tableheader = '\n'.join([
                                     '\n		<table class="sortable" id="eph">',\
                                     '		<tr> <th>Planet<br /><span class="small">[Link: Orbit ref.]</span></th>	  <th>Event<br /><span class="small">[Transit/<br />Eclipse]</span></th>	<th>Ingress <br /><span class="small">(MM/DD<br />HH:MM, UT)</span></th> <th>Egress <br /><span class="small">(MM/DD<br />HH:MM, (UT), Alt., Dir.)</span></th>'+\
                                     '<th>'+band.upper()+'</th> <th>Depth<br />(mag)</th> <th>Duration<br />(hrs)</th> <th>RA/Dec<br /><span class="small">[Link: Simbad ref.]</span></th> <th>Const.</th> <th>Mass<br />(M<sub>J</sub>)</th>'+\
                                     '<th>Radius<br />(R<sub>J</sub>)</th> <th>Ref. Year</th></tr>'])
        else:
            tableheader = '\n'.join([
                                     '\n        <table class="sortable" id="eph">',\
                                     '        <tr> <th>Planet<br /><span class="small">[Link: Orbit ref.]</span></th>      <th>Event<br /><span class="small">[Transit/<br />Eclipse]</span></th> <th>Ingress <br /><span class="small">(MM/DD<br />HH:MM (LT), Alt., Dir.)</span></th> <th>Egress <br /><span class="small">(MM/DD<br />HH:MM (LT), Alt., Dir.)</span></th>   '+\
                                     '<th>'+band.upper()+'</th> <th>Depth<br />(mag)</th> <th>Duration<br />(hrs)</th> <th>RA/Dec<br /><span class="small">[Link: Simbad ref.]</span></th> <th>Const.</th> <th>Mass<br />(M<sub>J</sub>)</th>'+\
                                     ' <th>Radius<br />(R<sub>J</sub>)</th> <th>Ref. Year</th> <th>Ingress <br /><span class="small">(MM/DD<br />HH:MM (UT))</span></th> <th>Egress <br /><span class="small">(MM/DD<br />HH:MM, (UT))</span></th></tr>'])
    
        
        tablefooter = '\n'.join([
                                 '\n		</table>',\
                                 '		<br /><br />',])
        htmlfooter = '\n'.join([
                                '\n		<p class="headinfo">',\
                                '		Developed by Brett Morris with great gratitude for the help of <a href="http://rhodesmill.org/pyephem/">PyEphem</a>,<br/>',\
                                '		and for up-to-date exoplanet parameters from <a href="http://www.exoplanets.org/">exoplanets.org</a> (<a href="http://adsabs.harvard.edu/abs/2011PASP..123..412W">Wright et al. 2011</a>).<br />',\
                                '		</p>',\
                                '		</div>',\
                                '	</body>',\
                                '</html>'])
        report.write(htmlheader)
        report.write(tableheader)
        
        allKeys = np.array(allKeys)[np.argsort(allKeys)]
        for key in allKeys:
            def writeHTMLtransit():
                indentation = '		'
                if show_lt != 0: 
                    middle = '</td><td>'.join([nameWithLink(planet[0]),str(planet[3]),list2datestrHTML_LT(jd2gd(float(planet[1]-planet[2])),planet[4],planet[5]),\
                                               list2datestrHTML_LT(jd2gd(float(planet[1]+planet[2])),planet[6],planet[7]),trunc(bandMagnitude(str(planet[0])),2),\
                                               trunc(depth(planet[0]),4),trunc(24.0*duration(planet[0]),2),RADecHTML(planet[0]),constellation(planet[0]),\
                                               mass(planet[0]),radius(planet[0]),orbitReferenceYear(planet[0]),list2datestrHTML_UTnoaltdir(jd2gd(float(planet[1]-planet[2])),planet[4],planet[5]),\
                                               list2datestrHTML_UTnoaltdir(jd2gd(float(planet[1]+planet[2])),planet[6],planet[7])])
                else:
                    middle = '</td><td>'.join([nameWithLink(planet[0]),str(planet[3]),list2datestrHTML(jd2gd(float(planet[1]-planet[2])),planet[4],planet[5]),\
                                               list2datestrHTML(jd2gd(float(planet[1]+planet[2])),planet[6],planet[7]),trunc(bandMagnitude(str(planet[0])),2),\
                                               trunc(depth(planet[0]),4),trunc(24.0*duration(planet[0]),2),RADecHTML(planet[0]),constellation(planet[0]),\
                                               mass(planet[0]),radius(planet[0]),orbitReferenceYear(planet[0])])
                line = indentation+'<tr><td>'+middle+'</td></tr>\n'
                report.write(line)
            
            def writeHTMLeclipse():
                indentation = '		'
                if show_lt != 0:
                    middle = '</td><td>'.join([nameWithLink(planet[0]),str(planet[3]),list2datestrHTML_LT(jd2gd(float(planet[1]-planet[2])),planet[4],planet[5]),\
                                               list2datestrHTML_LT(jd2gd(float(planet[1]+planet[2])),planet[6],planet[7]),trunc(bandMagnitude(str(planet[0])),2),\
                                               '---',trunc(24.0*duration(planet[0]),2),RADecHTML(planet[0]),constellation(planet[0]),\
                                               mass(planet[0]),radius(planet[0]),orbitReferenceYear(planet[0]),list2datestrHTML_UTnoaltdir(jd2gd(float(planet[1]-planet[2])),planet[4],planet[5]),\
                                               list2datestrHTML_UTnoaltdir(jd2gd(float(planet[1]+planet[2])),planet[6],planet[7])])
                else: 
                    middle = '</td><td>'.join([nameWithLink(planet[0]),str(planet[3]),list2datestrHTML(jd2gd(float(planet[1]-planet[2])),planet[4],planet[5]),\
                                               list2datestrHTML(jd2gd(float(planet[1]+planet[2])),planet[6],planet[7]),trunc(bandMagnitude(str(planet[0])),2),\
                                               '---',trunc(24.0*duration(planet[0]),2),RADecHTML(planet[0]),constellation(planet[0]),\
                                               mass(planet[0]),radius(planet[0]),orbitReferenceYear(planet[0])])

                line = indentation+'<tr><td>'+middle+'</td></tr>\n'
                report.write(line)
            
            
            if np.shape(events[key])[0] > 1:
                elapsedTime = []
                
                for i in range(1,len(events[key])):
                    nextPlanet = events[key][1]
                    planet = events[key][0]
                    double = False
                    '''If the other planet's ingress is before this one's egress, then'''
                    if ephem.Date(list2datestr(jd2gd(float(nextPlanet[1]-nextPlanet[2])))) -\
                        ephem.Date(list2datestr(jd2gd(float(planet[1]+planet[2])))) > 0.0:
                            double = True
                            elapsedTime.append(ephem.Date(list2datestr(jd2gd(float(nextPlanet[1]-nextPlanet[2])))) - \
                                               ephem.Date(list2datestr(jd2gd(float(planet[1]+planet[2])))))
                    
                    if ephem.Date(list2datestr(jd2gd(float(planet[1]-planet[2])))) - \
                        ephem.Date(list2datestr(jd2gd(float(nextPlanet[1]+nextPlanet[2])))) > 0.0:
                            '''If the other planet's egress is before this one's ingress, then'''
                            double = True
                            elapsedTime.append(ephem.Date(list2datestr(jd2gd(float(planet[1]-planet[2])))) - \
                                               ephem.Date(list2datestr(jd2gd(float(nextPlanet[1]+nextPlanet[2])))))
                
                for planet in events[key]:
                    if calcTransits and planet[3] == 'transit':
                        writeHTMLtransit()
                    if calcEclipses and planet[3] == 'eclipse':
                        writeHTMLeclipse()		  
            elif np.shape(events[key])[0] == 1:
                planet = events[key][0]
                if calcTransits and planet[3] == 'transit':
                    writeHTMLtransit()
                if calcEclipses and planet[3] == 'eclipse':
                    writeHTMLeclipse()
        report.write(tablefooter)
        report.write(htmlfooter)
        report.close()
    #print exoplanetDB['HD 209458 b']

