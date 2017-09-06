import collections

# Block and BlockReplica implemented as tuples to reduce memory footprint
Block = collections.namedtuple('Block', ['name', 'dataset', 'size', 'num_files', 'is_open'])

def _Block_translate_name(name_str):
    # block name format: [8]-[4]-[4]-[4]-[12] where [n] is an n-digit hex.
    return int(name_str.replace('-', ''), 16)

def _Block___str__(self):
    return 'Block %s#%s (size=%d, num_files=%d, is_open=%s)' % (self.dataset.name, self.real_name(), self.size, self.num_files, self.is_open)

def _Block_real_name(self):
    full_string = hex(self.name).replace('0x', '')[:-1] # last character is 'L'
    if len(full_string) < 32:
        full_string = '0' * (32 - len(full_string)) + full_string

    return full_string[:8] + '-' + full_string[8:12] + '-' + full_string[12:16] + '-' + full_string[16:20] + '-' + full_string[20:]

def _Block_clone(self, **kwd):
    return Block(
        self.name,
        self.dataset if 'dataset' not in kwd else kwd['dataset'],
        self.size if 'size' not in kwd else kwd['size'],
        self.num_files if 'num_files' not in kwd else kwd['num_files'],
        self.is_open if 'is_open' not in kwd else kwd['is_open']
    )

# LOCAL INSTANCE (TODO MAKE THIS NEATER)
#Block.translate_name = staticmethod(lambda name: name)
#Block.real_name = lambda self: self.name

Block.translate_name = staticmethod(_Block_translate_name) 
Block.real_name = _Block_real_name

Block.__str__ = _Block___str__
Block.clone = _Block_clone
