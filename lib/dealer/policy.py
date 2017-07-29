import logging
import collections
import random
import fnmatch
import time

import dealer.configuration as dealer_config

logger = logging.getLogger(__name__)

random.seed(time.time())

def target_site_def(site):
    matches = False
    for pattern in dealer_config.target_sites:
        if pattern.startswith('!'):
            if fnmatch.fnmatch(site.name, pattern[1:]):
                matches = False
        else:
            if fnmatch.fnmatch(site.name, pattern):
                matches = True

    return matches

class DealerPolicy(object):
    """
    Defined for each partition and implements the concrete conditions for copies.
    """

    def __init__(self, partition, group = None, version = ''):
        self.partition = partition
        self.group = group
        self.version = version
        # target site can change between policies, but we only have one policy running at the moment
        self.target_site_def = target_site_def
        self.used_demand_plugins = set()
        
        self._request_plugins = []

    def add_plugin(self, plugin, priority = 1):
        """
        Add a plugin with a priority factor. Request from a plugin is picked up
        at a rate proportional to the inverse of the priority factor.
        Algorithm:
        For n plugins with priority factors p_i (i=0,...,n-1),
        P = sum_i(1/p_i)
        R_i = (1/p_i) / P
        
        @param plugin    Dealer plugin object
        @param priority  Priority factor
        """

        zero_prio = [(p, 0) for p, r in self._request_plugins if r == 0]

        if priority == 0:
            if len(self._request_plugins) != 0:
                logger.warning('Throwing away existing plugins to make away for zero-priority plugin %s.', plugin.name)

            self._request_plugins = zero_prio + [(plugin, 0)]
        else:
            if len(zero_prio) != 0:
                raise RuntimeError('Plugins with priority == 0 exist. Cannot add a plugin with finite priority.')

            self._request_plugins.append((plugin, priority))

        self.used_demand_plugins.update(plugin.used_demand_plugins)

    def collect_requests(self, inventory, target_sites):
        """
        Collect requests from each plugin and return a prioritized list.
        @param inventory     An InventoryManager instance.
        @param target_sites  A set of target sites for plugins that specify the destinations.
        """

        reqlists = []

        for plugin, priority in self._request_plugins:
            if priority == 0:
                # all plugins must have priority 0 (see add_plugin)
                # -> treat all as equal.
                priority = 1

            plugin_requests = plugin.get_requests(inventory, self, target_sites)

            logger.debug('%s requesting %d items', plugin.name, len(plugin_requests))

            if len(plugin_requests) != 0:
                reqlists.append((plugin_requests, plugin, priority))

        requests = []

        while len(reqlists) != 0:
            pvalues = [1. / r for l, p, r in reqlists]
            sums = [sum(pvalues[:i + 1]) for i in range(len(pvalues))]

            # Classic weighted random-picking algorithm
            # Select k if sum(w_{i})_{i <= k-1} w_{k} < x < sum(w_{i})_{i <= k} for x in Uniform(0, sum(w_{i}))
            x = random.uniform(0., sums[-1])

            ip = next(k for k in range(len(sums)) if x < sums[k])

            reqlist = reqlists[ip][0]
            requests.append(reqlist.pop(0))

            if len(reqlist) == 0:
                logger.debug('No more requests from %s', reqlists[ip][1].name)
                reqlists.pop(ip)

        return requests

    def record(self, run_number, history, copy_list):
        for plugin, priority in self._request_plugins:
            plugin.save_record(run_number, history, copy_list)
