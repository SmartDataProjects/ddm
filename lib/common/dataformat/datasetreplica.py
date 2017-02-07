import time
import collections

class DatasetReplica(object):
    """Represents a dataset replica. Combines dataset and site information."""

    # Access types.
    # Starting from 1 to play better with MySQL.
    ACC_LOCAL, ACC_REMOTE = range(1, 3)
    Access = collections.namedtuple('Access', ['num_accesses', 'cputime'])

    def __init__(self, dataset, site, is_complete = False, is_custodial = False, last_block_created = 0):
        self.dataset = dataset
        self.site = site
        self.is_complete = is_complete # = complete subscription. Can still be partial
        self.is_custodial = is_custodial
        self.last_block_created = last_block_created
        self.block_replicas = []
        self.accesses = {DatasetReplica.ACC_LOCAL: {}, DatasetReplica.ACC_REMOTE: {}} # UTC date -> Accesses

    def unlink(self):
        self.dataset.replicas.remove(self)
        self.dataset = None

        self.site.dataset_replicas.remove(self)

        for block_replica in self.block_replicas:
            self.site.remove_block_replica(block_replica)

        self.block_replicas = []
        self.site = None

    def __str__(self):
        return 'DatasetReplica {site}:{dataset} (is_complete={is_complete}, is_custodial={is_custodial},' \
            ' {block_replicas_size} block_replicas,' \
            ' #accesses[LOCAL]={num_local_accesses}, #accesses[REMOTE]={num_remote_accesses})'.format(
                site = self.site.name, dataset = self.dataset.name, is_complete = self.is_complete,
                is_custodial = self.is_custodial,
                block_replicas_size = len(self.block_replicas),
                num_local_accesses = len(self.accesses[DatasetReplica.ACC_LOCAL]),
                num_remote_accesses = len(self.accesses[DatasetReplica.ACC_REMOTE]))

    def __repr__(self):
        rep = 'DatasetReplica(%s,\n' % repr(self.dataset)
        rep += '    %s,\n' % repr(self.site)
        rep += '    is_complete=%s,\n' % str(self.is_complete)
        rep += '    is_custodial=%s,\n' % str(self.is_custodial)
        rep += '    last_block_created=%d)' % self.last_block_created

        return rep

    def clone(self, block_replicas = True):
        # Create a detached clone. Detached in the sense that it is not linked from dataset or site.
        replica = DatasetReplica(dataset = self.dataset, site = self.site, is_complete = self.is_complete, is_custodial = self.is_custodial, last_block_created = self.last_block_created)

        if block_replicas:
            for brep in self.block_replicas:
                replica.block_replicas.append(brep.clone())

        return replica

    def is_last_copy(self):
        return len(self.dataset.replicas) == 1 and self.dataset.replicas[0] == self

    def is_partial(self):
        return self.is_complete and len(self.block_replicas) != len(self.dataset.blocks)

    def is_full(self):
        return self.is_complete and len(self.block_replicas) == len(self.dataset.blocks)

    def size(self, groups = [], physical = True):
        if type(groups) is not list:
            # single group given
            if physical:
                return sum([r.size for r in self.block_replicas if r.group == groups])
            else:
                return sum([r.block.size for r in self.block_replicas if r.group == groups])

        else: # expect a list
            if len(groups) == 0:
                # no group spec
                if self.is_full():
                    return self.dataset.size()
                else:
                    if physical:
                        return sum([r.size for r in self.block_replicas])
                    else:
                        return sum([r.block.size for r in self.block_replicas])

            else:
                if physical:
                    return sum([r.size for r in self.block_replicas if r.group in groups])
                else:
                    return sum([r.block.size for r in self.block_replicas if r.group in groups])

    def find_block_replica(self, block):
        try:
            if type(block).__name__ == 'Block':
                return next(b for b in self.block_replicas if b.block == block)
            else:
                return next(b for b in self.block_replicas if b.block.name == block)

        except StopIteration:
            return None

    def last_access(self):
        try:
            last_datetime = max(replica.accesses[DatasetReplica.ACC_LOCAL].keys() + replica.accesses[DatasetReplica.ACC_REMOTE].keys())
        except:
            return 0

        return time.mktime(last_datetime.utctimetuple())

