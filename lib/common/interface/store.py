import logging
import time

from common.dataformat import Dataset, Block, Site, IntegrityError
import common.configuration as config

logger = logging.getLogger(__name__)

class LocalStoreInterface(object):
    """
    Interface to local inventory data store.
    """

    class LockError(Exception):
        pass

    CLEAR_NONE = 0
    CLEAR_REPLICAS = 1
    CLEAR_ALL = 2

    def __init__(self):
        # Allow multiple calls to acquire-release. No other process can acquire
        # the lock until the depth in this process is 0.
        self._lock_depth = 0

        self.last_update = 0

    def acquire_lock(self, blocking = True):
        if self._lock_depth == 0:
            locked = self._do_acquire_lock(blocking)
            if not locked: # only happens when not blocking
                return False

        self._lock_depth += 1
        return True

    def release_lock(self, force = False):
        if self._lock_depth == 1 or force:
            self._do_release_lock(force)

        if self._lock_depth > 0: # should always be the case if properly programmed
            self._lock_depth -= 1

    def get_last_update(self):
        logger.debug('_do_get_last_update()')

        self.acquire_lock()
        try:
            return self._do_get_last_update()
        finally:
            self.release_lock()

    def set_last_update(self, tm = -1):
        if tm < 0:
            tm = time.time()

        self.last_update = tm

        if config.read_only:
            logger.debug('_do_set_last_update(%f)', tm)
            return

        self.acquire_lock()
        try:
            self._do_set_last_update(tm)
        finally:
            self.release_lock()

    def make_snapshot(self, clear = CLEAR_NONE, tag = ''):
        """
        Make a snapshot of the current state of the persistent inventory. Flag clear = True
        will "move" the data into the snapshot, rather than cloning it.
        Tag is normally, but is not restricted to be, a timestamp.
        """

        if not tag:
            tag = time.strftime('%y%m%d%H%M%S')

        if config.read_only:
            logger.debug('_do_make_snapshot(%s, %d)', tag, clear)
            return

        self.acquire_lock()
        try:
            self._do_make_snapshot(tag, clear)
        finally:
            self.release_lock()

        return tag

    def remove_snapshot(self, tag = '', newer_than = 0, older_than = 0):
        if not tag and older_than == 0:
            older_than = time.time()

        if config.read_only:
            logger.debug('_do_remove_snapshot(%s, %f, %f)', tag, newer_than, older_than)
            return

        self.acquire_lock()
        try:
            self._do_remove_snapshot(tag, newer_than, older_than)
        finally:
            self.release_lock()

    def list_snapshots(self, timestamp_only = False):
        """
        List the tags of the inventory snapshots that is not the current.
        """

        return self._do_list_snapshots(timestamp_only)

    def clear(self):
        """
        Wipes out the store contents!!
        """

        if config.read_only:
            logger.debug('_do_clear()')
            return

        self.acquire_lock()
        try:
            self._do_clear()
        finally:
            self.release_lock()

    def recover_from(self, tag):
        """
        Recover store contents from a snapshot (current content will be lost!)
        timestamp can be 'last'.
        """

        if tag == 'last':
            tags = self.list_snapshots(timestamp_only = True)
        else:
            tags = self.list_snapshots()

        if len(tags) == 0:
            logger.info('No snapshots taken.')
            return

        if tag == 'last':
            tag = tags[0]
            logger.info('Recovering inventory store from snapshot %s', tag)
            
        elif tag not in tags:
            logger.info('Cannot copy from snapshot %s', tag)
            return

        while self._lock_depth > 0:
            self.release_lock()

        self._do_recover_from(tag)

    def switch_snapshot(self, tag):
        """
        Switch to a specific snapshot.
        timestamp can be 'last'.
        """

        if tag == 'last':
            tags = self.list_snapshots(timestamp_only = True)
        else:
            tags = self.list_snapshots()

        if len(tags) == 0:
            logger.info('No snapshots taken.')
            return

        if tag == 'last':
            tag = tags[0]
            logger.info('Switching inventory store to snapshot %s', tag)
            
        elif tag not in tags:
            logger.info('Cannot switch to snapshot %s', tag)
            return

        while self._lock_depth > 0:
            self.release_lock()

        self._do_switch_snapshot(tag)

    def get_site_list(self, include = ['*'], exclude = []):
        """
        Return a list of site names. Argument site_filt can be a wildcard string or a list of wildcards.
        """

        logger.debug('_do_get_site_list()')
        
        self.acquire_lock()
        try:
            site_names = self._do_get_site_list(include, exclude)
        finally:
            self.release_lock()

        return site_names

    def load_data(self, site_filt = '*', dataset_filt = '*', load_blocks = False, load_files = False, load_replicas = True):
        """
        Return lists loaded from persistent storage. Argument site_filt can be a wildcard string or a list
        of exact site names.
        """

        logger.debug('_do_load_data()')

        self.acquire_lock()
        try:
            site_list, group_list, dataset_list = self._do_load_data(site_filt, dataset_filt, load_blocks, load_files, load_replicas)
        finally:
            self.release_lock()

        return site_list, group_list, dataset_list

    def load_dataset(self, dataset_name, load_blocks = False, load_files = False, load_replicas = False, sites = None, groups = None):
        """
        Load a dataset and create a Dataset object.
        """

        logger.debug('_do_load_dataset()')

        if load_replicas and (sites is None or groups is None):
            raise RuntimeError('Cannot load replicas without sites or groups')

        self.acquire_lock()
        try:
            dataset = self._do_load_dataset(dataset_name, load_blocks, load_files, load_replicas, sites, groups)
        finally:
            self.release_lock()

        return dataset

    def load_replicas(self, dataset, sites = None, groups = None):
        """
        Load replicas for the given dataset.
        """

        logger.debug('_do_load_replicas()')

        self.acquire_lock()
        try:
            self._do_load_replicas(dataset, sites, groups)
        finally:
            self.release_lock()

    def load_blocks(self, dataset):
        """
        Load blocks for the given dataset.
        """

        logger.debug('_do_load_blocks()')

        self.acquire_lock()
        try:
            self._do_load_blocks(dataset)
        finally:
            self.release_lock()

    def load_files(self, dataset):
        """
        Load files for the given dataset.
        """

        logger.debug('_do_load_files()')
        
        self.acquire_lock()
        try:
            self._do_load_files(dataset)
        finally:
            self.release_lock()

    def check_if_on(self, datasetname, sitename):
        """
        Return true/false if replica is on specific site.
        """

        logger.debug('_do_check_if_on()')

        return self._do_check_if_on(datasetname, sitename)

    def find_block_of(self, fullpath, datasets):
        """
        Return the Block object for the given file.
        """

        logger.debug('_do_find_block_of()')

        return self._do_find_block_of(fullpath, datasets)

    def load_replica_accesses(self, sites, datasets):
        """
        @param sites    List of sites
        @param datasets List of datasets
        @returns (last update date, {replica: {date: num_access}})
        """

        logger.debug('_do_load_replica_accesses()')

        self.acquire_lock()
        try:
            return self._do_load_replica_accesses(sites, datasets)
        finally:
            self.release_lock()

    def load_dataset_requests(self, datasets):
        """
        @param datasets  List of datasets
        @returns (last update unix timestamp, {dataset: {job_id: (queue_time, completion_time, nodes_total, nodes_done, nodes_failed, nodes_queued)}})
        """

        logger.debug('_do_load_dataset_requests()')

        self.acquire_lock()
        try:
            return self._do_load_dataset_requests(datasets)
        finally:
            self.release_lock()

    def save_data(self, sites, groups, datasets, timestamp = -1, delta = True):
        """
        Write information in memory into persistent storage.
        Remove information of datasets and blocks with no replicas.
        Arguments are list of objects.
        @param sites    list of sites
        @param groups   list of groups
        @param datasets list of datasets
        @param delta    incrementally update the replicas
        """

        if config.read_only:
            logger.debug('_do_save_data()')
            return

        self.acquire_lock()
        try:
            self._do_save_sites(sites)
            self._do_save_groups(groups)
            self._do_save_datasets(datasets)
            if delta:
                self._do_update_replicas(sites, groups, datasets)
            else:
                self._do_save_replicas(sites, groups, datasets)

            self.set_last_update(timestamp)
        finally:
            self.release_lock()

    def save_sites(self, sites):
        """
        Write information in memory into persistent storage.
        Argument is a list of sites.
        """

        if config.read_only:
            logger.debug('_do_save_sites()')
            return

        self.acquire_lock()
        try:
            self._do_save_sites(sites)
            self.set_last_update()
        finally:
            self.release_lock()

    def save_groups(self, groups):
        """
        Write information in memory into persistent storage.
        Argument is a list of groups.
        """

        if config.read_only:
            logger.debug('_do_save_groups()')
            return

        self.acquire_lock()
        try:
            self._do_save_groups(groups)
            self.set_last_update()
        finally:
            self.release_lock()

    def save_datasets(self, datasets):
        """
        Write information in memory into persistent storage.
        Argument is a list of datasets.
        """

        if config.read_only:
            logger.debug('_do_save_data()')
            return

        self.acquire_lock()
        try:
            self._do_save_datasets(datasets)
            self.set_last_update()
        finally:
            self.release_lock()

    def save_replica_accesses(self, access_list):
        """
        Write information in memory into persistent storage.
        @param access_list  {replica: {date: (num_access, cputime)}}
        """

        if config.read_only:
            logger.debug('_do_save_replica_accesses()')
            return

        self.acquire_lock()
        try:
            self._do_save_replica_accesses(access_list)
            self.set_last_update()
        finally:
            self.release_lock()

    def save_dataset_requests(self, request_list):
        """
        Write information in memory into persistent storage.
        @param request_list  Data on updated requests. Same format as load_dataset_request return value [1]
        """

        if config.read_only:
            logger.debug('_do_save_dataset_requests()')
            return

        self.acquire_lock()
        try:
            self._do_save_dataset_requests(request_list)
            self.set_last_update()
        finally:
            self.release_lock()

    def add_datasetreplicas(self, replicas):
        """
        Insert a few replicas instead of saving the full list.
        """

        if config.read_only:
            logger.debug('_do_add_datasetreplicas()')
            return

        self.acquire_lock()
        try:
            self._do_add_datasetreplicas(replicas)
            self.set_last_update()
        finally:
            self.release_lock()

    def add_blockreplicas(self, replicas):
        """
        Insert a few replicas instead of saving the full list.
        """

        if config.read_only:
            logger.debug('_do_add_blockreplicas()')
            return

        self.acquire_lock()
        try:
            self._do_add_blockreplicas(replicas)
            self.set_last_update()
        finally:
            self.release_lock()

    def delete_dataset(self, dataset):
        """
        Delete dataset from persistent storage.
        """

        if config.read_only:
            logger.debug('_do_delete_dataset(%s)', dataset.name)
            return

        self.acquire_lock()
        try:
            self._do_delete_dataset(dataset)
        finally:
            self.release_lock()

    def delete_datasets(self, datasets):
        """
        Delete datasets from persistent storage.
        """

        if config.read_only:
            logger.debug('_do_delete_datasets()')
            return

        self.acquire_lock()
        try:
            self._do_delete_datasets(datasets)
        finally:
            self.release_lock()

    def delete_block(self, block):
        """
        Delete block from persistent storage.
        """

        if config.read_only:
            logger.debug('_do_delete_block(%s)', block.real_name())
            return

        self.acquire_lock()
        try:
            self._do_delete_block(block)
        finally:
            self.release_lock()

    def delete_datasetreplica(self, replica, delete_blockreplicas = True):
        """
        Delete dataset replica from persistent storage.
        If delete_blockreplicas is True, delete block replicas associated to this dataset replica too.
        """

        if config.read_only:
            logger.debug('_do_delete_datasetreplica(%s:%s)', replica.site.name, replica.dataset.name)
            return

        self.delete_datasetreplicas([replica], delete_blockreplicas = delete_blockreplicas)

    def delete_datasetreplicas(self, replica_list, delete_blockreplicas = True):
        """
        Delete a set of dataset replicas from persistent storage.
        If delete_blockreplicas is True, delete block replicas associated to the dataset replicas too.
        """

        if config.read_only:
            logger.debug('_do_delete_datasetreplicas(%d replicas)', len(replica_list))
            return

        sites = list(set([r.site for r in replica_list]))
        datasets_on_site = dict([(site, []) for site in sites])
        
        for replica in replica_list:
            datasets_on_site[replica.site].append(replica.dataset)

        self.acquire_lock()
        try:
            for site in sites:
                self._do_delete_datasetreplicas(site, datasets_on_site[site], delete_blockreplicas)
        finally:
            self.release_lock()

    def delete_blockreplica(self, replica):
        """
        Delete block replica from persistent storage.
        """

        if config.read_only:
            logger.debug('_do_delete_blockreplica(%s:%s)', replica.site.name, replica.block.real_name())
            return

        self.delete_blockreplicas([replica])

    def delete_blockreplicas(self, replica_list):
        """
        Delete a set of block replicas from persistent storage.
        """

        if config.read_only:
            logger.debug('_do_delete_blockreplicas(%d replicas)', len(replica_list))
            return

        self.acquire_lock()
        try:
            self._do_delete_blockreplicas(replica_list)
        finally:
            self.release_lock()

    def update_blockreplica(self, replica):
        """
        Update block replica in persistent storage.
        """

        if config.read_only:
            logger.debug('_do_update_blockreplica(%s:%s)', replica.site.name, replica.block.real_name())
            return

        self.update_blockreplicas([replica])

    def update_blockreplicas(self, replica_list):
        """
        Update a set of block replicas in persistent storage.
        """

        if config.read_only:
            logger.debug('_do_update_blockreplicas(%d replicas)', len(replica_list))
            return

        self.acquire_lock()
        try:
            self._do_update_blockreplicas(replica_list)
        finally:
            self.release_lock()

    def set_dataset_status(self, dataset, status):
        """
        Set and save dataset status
        """

        # convert status into a string
        status_str = Dataset.status_name(status)

        if type(dataset) is Dataset:
            dataset_name = dataset.name
        elif type(dataset) is str:
            dataset_name = dataset

        if config.read_only:
            logger.debug('_do_set_dataset_status(%s, %s)', dataset.name, status_str)
            return

        self.acquire_lock()
        try:
            self._do_set_dataset_status(dataset_name, status_str)
        finally:
            self.release_lock()


if __name__ == '__main__':

    import sys
    from argparse import ArgumentParser
    import common.interface.classes as classes

    parser = ArgumentParser(description = 'Local inventory store interface')

    parser.add_argument('command', metavar = 'COMMAND', help = '(help|snapshot [clear (replicas|all)]|clear|clean|restore|list (datasets|groups|sites)|show (dataset|block|site|replica) <name>|lock|release)')
    parser.add_argument('arguments', metavar = 'ARGS', nargs = '*', help = '')
    parser.add_argument('--class', '-c', metavar = 'CLASS', dest = 'class_name', default = '', help = 'LocalStoreInterface class to be used.')
    parser.add_argument('--tag', '-t', metavar = 'YMDHMS', dest = 'tag', default = '', help = 'Tag of the snapshot to be loaded / cleaned. With command clean and a timestamp tag, prepend with "<" or ">" to remove all snapshots older or newer than the timestamp.')

    args = parser.parse_args()
    sys.argv = []

    if args.class_name == '':
        interface = classes.default_interface['store']()
    else:
        interface = getattr(classes, args.class_name)()

    if args.command == 'help':
        pass

    elif args.command == 'snapshot':
        clear = LocalStoreInterface.CLEAR_NONE
        if len(args.arguments) > 1 and args.arguments[0] == 'clear':
            if args.arguments[1] == 'replicas':
                clear = LocalStoreInterface.CLEAR_REPLICAS
            elif args.arguments[1] == 'all':
                clear = LocalStoreInterface.CLEAR_ALL

        interface.make_snapshot(clear = clear, tag = args.tag)

    elif args.command == 'clear':
        interface.clear()

    elif args.command == 'clean':
        tag = ''
        newer_than = time.time()
        older_than = 0

        if not args.tag:
            newer_than = 0
            older_than = time.time()
        elif args.tag.startswith('>'):
            newer_than = time.mktime(time.strptime(args.tag[1:], '%y%m%d%H%M%S'))
            older_than = time.time()
        elif args.tag.startswith('<'):
            newer_than = 0
            older_than = time.mktime(time.strptime(args.tag[1:], '%y%m%d%H%M%S'))
        else:
            tag = args.tag

        interface.remove_snapshot(tag = tag, newer_than = newer_than, older_than = older_than)

    elif args.command == 'restore':
        if not args.tag:
            print 'Specify a tag (can be "last").'
            sys.exit(1)

        interface.recover_from(args.tag)

    elif args.command == 'list':
        if args.tag:
            interface.switch_snapshot(args.tag)

        if args.arguments[0] != 'snapshots':
            sites, groups, datasets = interface.load_data()
    
            if args.arguments[0] == 'datasets':
                print [d.name for d in datasets]
    
            elif args.arguments[0] == 'groups':
                print [g.name for g in groups]
    
            elif args.arguments[0] == 'sites':
                print [s.name for s in sites]

        else:
            for snapshot in interface.list_snapshots():
                print snapshot

    elif args.command == 'show':
        if args.tag:
            interface.switch_snapshot(args.tag)

        if args.arguments[0] == 'dataset':
            sites, groups, datasets = interface.load_data(dataset_filt = args.arguments[1])

            try:
                dataset = next(d for d in datasets if d.name == args.arguments[1])
            except StopIteration:
                print 'No dataset %s found.' % args.arguments[1]
                sys.exit(0)

            print dataset

        elif args.arguments[0] == 'block':
            dataset_name, sep, block_name = args.arguments[1].partition('#')
            sites, groups, datasets = interface.load_data(dataset_filt = dataset_name)

            try:
                dataset = next(d for d in datasets if d.name == dataset_name)
            except StopIteration:
                print 'No dataset %s found.' % dataset
                sys.exit(0)

            block = dataset.find_block(Block.translate_name(block_name))
            if block is None:
                print 'No block %s found in dataset %s.' % (block_name, dataset.name)
                sys.exit(0)

            print block

        elif args.arguments[0] == 'site':
            sites, groups, datasets = interface.load_data(site_filt = args.arguments[1])

            try:
                site = next(s for s in sites if s.name == args.arguments[1])
            except StopIteration:
                print 'No site %s found.' % args.arguments[1]
                sys.exit(0)

            print site

        elif args.arguments[0] == 'replica':
            site_name, sep, obj_name = args.arguments[1].partition(':')
            if '#' in obj_name:
                dataset_name, sep, block_name = obj_name.partition('#')
            else:
                dataset_name = obj_name
                block_name = ''

            sites, groups, datasets = interface.load_data(site_filt = site_name, dataset_filt = dataset_name)
            interface.load_replica_accesses(sites, datasets)
            
            try:
                dataset = next(d for d in datasets if d.name == dataset_name)
            except StopIteration:
                print 'No dataset %s found.' % dataset
                sys.exit(0)

            replica = dataset.find_replica(site_name)
            if replica is None:
                print 'No replica %s found.' % args.arguments[1]
                sys.exit(0)

            if block_name != '':
                replica = replica.find_block_replica(Block.translate_name(block_name))
                if replica is None:
                    print 'No replica %s found.' % args.arguments[1]
                    sys.exit(0)

            print replica

    elif args.command == 'set_dataset_status':
        interface.set_dataset_status(args.arguments[0], args.arguments[1])

    elif args.command == 'set_last_update':
        interface.set_last_update(int(args.arguments[0]))

    elif args.command == 'lock':
        if len(args.arguments) > 0 and args.arguments[0] == 'block':
            interface.acquire_lock(blocking = True)
        else:
            interface.acquire_lock(blocking = False)

    elif args.command == 'release':
        interface.release_lock(force = True)
