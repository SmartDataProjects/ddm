import sys
import logging
import re
import socket
import htcondor

LOG = logging.getLogger(__name__)

class HTCondor(object):
    """
    HTCondor interface.
    """

    def __init__(self, config):
        self._collector = htcondor.Collector(config.collector)

        LOG.debug('Finding schedds reporting to collector %s', config.collector)

        self._schedds = []

        attempt = 0
        while True:
            try:
                schedd_ads = self._collector.query(htcondor.AdTypes.Schedd, config.schedd_constraint, ['MyAddress'])
                break
            except IOError:
                attempt += 1
                LOG.warning('Collector query failed: %s', str(sys.exc_info()[0]))
                if attempt == 10:
                    LOG.error('Communication with the collector failed. We have no information of the condor pool.')
                    return

        for ad in schedd_ads:
            schedd = htcondor.Schedd(ad)
            matches = re.match('<([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+):([0-9]+)', ad['MyAddress'])
            # schedd does not have an ipaddr attribute natively, but we can assign it
            schedd.ipaddr = matches.group(1)
            schedd.host = socket.getnameinfo((matches.group(1), int(matches.group(2))), socket.AF_INET)[0] # socket.getnameinfo(*, AF_INET) returns a (host, port) 2-tuple

            self._schedds.append(schedd)

        LOG.debug('Found schedds: %s', ', '.join(['%s (%s)' % (schedd.host, schedd.ipaddr) for schedd in self._schedds]))

    def find_jobs(self, constraint = 'True', attributes = []):
        """
        Return ClassAds for jobs matching the constraints.
        """

        LOG.debug('Querying HTCondor with constraint "%s" for attributes %s', constraint, str(attributes))

        classads = []

        for schedd in self._schedds:
            attempt = 0
            while True:
                try:
                    ads = schedd.query(constraint, attributes)
                    break
                except IOError:
                    attempt += 1
                    LOG.warning('IOError in communicating with schedd %s. Trying again.', schedd.ipaddr)
                    if attempt == 10:
                        LOG.error('Schedd %s did not respond.', schedd.ipaddr)
                        ads = []
                        break
                
            classads.extend(ads)

        LOG.info('HTCondor returned %d classads', len(classads))

        return classads
