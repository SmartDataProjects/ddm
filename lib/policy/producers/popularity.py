from pop.engine import engine

class FilePopularity(object):
    """
    Extracts the file usage.
    Sets one attr:
      last_access:  timestamp
      num_access:   int
    """

    produces = ['last_access', 'num_access']

    def __init__(self, config):
        self.pop_engine = engine()
        self.namespaces = config.namespaces

    def load(self, inventory):

        # need namespace
        for namespace in self.namespaces:

            usage_summary = self.pop_engine.get_namespace_usage_summary(namespace)
    
            for (name,n_accesses,last_access) in usage_summary:
    
                lfn = namespace + name
                file_object = inventory.find_file(lfn)
                attribute = file_object.block.dataset.attr
    
                if 'num_access' not in attribute:
                    attribute['num_access'] = n_access
                else:
                    attribute['num_access'] += n_access
    
                if 'last_access' not in attribute:
                    attribute['last_access'] = access
                elif attribute['last_access'] < access:
                    attribute['last_access'] = access
