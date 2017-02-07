class ReplicaInfoSourceInterface(object):
    """
    Interface specs for probe to the replica information source.
    """

    def __init__(self):
        pass

    def get_dataset_names(self, sites = [], groups = [], filt = '/*/*/*'):
        """
        Return a list of dataset names on the given site.
        Argument groups is a name->group dict.
        """

        return []

    def find_tape_copies(self, datasets):
        """
        Set on_tape properties of datasets with on_tape != TAPE_FULL.
        """
        pass

    def make_replica_links(self, sites, groups, datasets):
        """
        Link the sites with datasets and blocks.
        Arguments are name->obj maps
        """
        pass

class ReplicaInfoSourceDirect(ReplicaInfoSourceInterface):
    def __init__(self):
        pass

    def get_dataset_names(self, sites = [], groups = [], filt = '/*/*/*'):
        """                                                                                                  
        Return a list of dataset names on the given site.                                                    
        Argument groups is a name->group dict.                                                               
        """

        return []

    def find_tape_copies(self, datasets):
        """                                                                                                  
        Set on_tape properties of datasets with on_tape != TAPE_FULL.                                        
        """
        pass

    def make_replica_links(self, sites, groups, datasets):
        """
        Link the sites with datasets and blocks.
        Arguments are name->obj maps
        """
        print "check if I run"
        print sites
        print groups
        print datasets
        

        pass
