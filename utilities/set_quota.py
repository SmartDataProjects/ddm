#!/usr/bin/env python

"""
Usage examples:
Relative:
/usr/bin/python setQuota.py --scale 1.2 --site T2_US_MIT --partition Physics
Absolute:
/usr/bin/python setQuota.py --volume 999 --site T2_US_MIT --partition DataOps (--adjust_other)
"""

import sys
import re
import fnmatch

try:
    from dynamo.dataformat import SitePartition
except:
    pass

def update_quota(site_partition, new_quota, changed):
    site = site_partition.site
    partition = site_partition.partition

    if partition.subpartitions is not None:
        if site_partition.quota == 0:
            sys.stderr.write('Quota for %s at %s is 0. Please set the subpartition quotas first.\n' % (site.name, partition.name))
            sys.exit(1)

        # this is a super partition - doesn't have a quota of its own
        for subp in partition.subpartitions:
            site_subp = site.partitions[subp]
            sub_quota = int(float(site_subp.quota) / site_partition.quota * new_quota)
            update_quota(site_subp, sub_quota, changed)

    else:
        clone = SitePartition(site, partition, new_quota)
        changed.append(clone)

if __name__ == '__main__':
    from argparse import ArgumentParser

    desc = '''Use this script to change the quota of site partitions.
When used against a superpartition (partition with subpartitions), subpartition
quotas are scaled keeping the current proportions. When used against a subpartition,
the other partitions are adjusted only if --adjust-other option is used.'''

    parser = ArgumentParser(description = desc)

    parser.add_argument('--site', '-s', metavar = 'SITE', dest = 'site', help = 'Site name.', nargs='+')
    parser.add_argument('--partition', '-g', metavar = 'PARTITION', dest = 'partition', help = 'Partition name.')
    parser.add_argument('--volume', '-v', metavar = 'VOLUME', dest = 'volume', type = int, help = 'Size of partition in TB.')
    parser.add_argument('--scale', '-c', metavar = 'FACTOR', dest = 'scale', type = float, help = 'Scale the quota by a factor.')
    parser.add_argument('--adjust-other', '-a', action = 'store_true', dest = 'adjust_other', help = 'Automatically adjust the other subpartitions to keep the superpartition quota same? Default: False')
    parser.add_argument('--dump', '-d', action = 'store_true', dest = 'dump', help = 'Just print all of them. Default: False')
    
    args = parser.parse_args()
    sys.argv = []

    from dynamo.core.executable import inventory

    ## Check argument sanity

    if args.dump:
        if args.volume is not None or args.scale is not None:
            sys.stderr.write('--volume and --scale options are invalid for dumping.\n')
            sys.exit(2)
    else:
        if args.site is None:
            sys.stderr.write('--site option is required if not dumping.\n')
            sys.exit(2)

        if args.partition is None:
            sys.stderr.write('--partition option is required if not dumping.\n')
            sys.exit(2)
    
        if args.volume is None and args.scale is None:
            sys.stderr.write('--volume or --scale must be set.\n')
            sys.exit(2)
        elif args.volume is not None and args.scale is not None:
            sys.stderr.write('--volume and --scale cannot be used at the same time.\n')
            sys.exit(2)

    if args.partition is not None and args.partition not in inventory.partitions:
        sys.stderr.write("Invalid partition name %s.\n" % args.partition)
        sys.exit(2)

    ## Print the current quotas

    if args.site is None:
        site_names = sorted(inventory.sites.keys())
    else:
        site_names = []
        site_patterns = {}
        for pattern in args.site:
            site_patterns[pattern] = re.compile(fnmatch.translate(pattern))
        for key, pattern in site_patterns.iteritems():
            at_least_one_match = False
            for site in inventory.sites.keys():
                if pattern.match(site) and site not in site_names:
                    site_names.append(site)
                    at_least_one_match = True
            if not at_least_one_match:
                sys.stderr.write("Could not find site(s) matching %s.\n" % key)
                sys.exit(2) 

    if args.partition is None:
        partition_names = sorted(inventory.partitions.keys())
    else:
        partition_names = [args.partition]

    print "\nCurrent quota "

    for site_name in site_names:
        site = inventory.sites[site_name]
        
        for partition_name in partition_names:
            partition = inventory.partitions[partition_name]

            print "Site %16s | Partition %10s | Quota %6i TB" % (site.name, partition.name, site.partitions[partition].quota * 1.e-12)

    if args.dump:
        sys.exit(0)


    for sitetmp in site_names:
        ## Compute the new quotas
        
        changed = []

        site = inventory.sites[sitetmp]
        partition = inventory.partitions[args.partition]

        site_partition = site.partitions[partition]

        if args.scale:
            args.volume = int(site_partition.quota * args.scale * 1.e-12)

        new_quota = args.volume * 1.e+12

        if partition.parent is not None and args.adjust_other:
            others_total_new = site.partitions[partition.parent].quota - new_quota

            if others_total_new < 0:
                sys.stderr.write('Cannot set quota for subpartition %s to be greater than the total quota for %s\n' % (partition.name, partition.parent.name))
                sys.exit(1)

            # this is a subpartition
            others_total_current = 0
            for subp in partition.parent.subpartitions:
                if subp is not partition:
                    others_total_current += site.partitions[subp].quota

            for subp in partition.parent.subpartitions:
                if subp is not partition:
                    site_subp = site.partitions[subp]
                    new_subp_quota = int(float(site_subp.quota) / others_total_current * others_total_new)
                    update_quota(site_subp, new_subp_quota, changed)
    
        update_quota(site_partition, new_quota, changed)

        ## Summarize

        print "\nQuota changes"

        for sp in changed:
            part = inventory.partitions[sp.partition.name]
            print "Site %16s | Partition %10s | Quota %6i -> %6i TB" % (site.name, part.name, site.partitions[part].quota * 1.e-12, sp.quota * 1.e-12)
            inventory.update(sp)

        print "Done."
