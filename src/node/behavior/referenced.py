import uuid
from zope.interface import implements
from zope.interface.common.mapping import IReadMapping
from node.interfaces import IReferenced
from node.meta import (
    behavior,
    before,
    after,
    BaseBehavior,
)

class NodeIndex(object):
    implements(IReadMapping)

    def __init__(self, index):
        self._index = index

    def __getitem__(self, key):
        return self._index[int(key)]

    def get(self, key, default=None):
        return self._index.get(int(key), default)

    def __contains__(self, key):
        return int(key) in self._index


class Referenced(BaseBehavior):
    implements(IReferenced)
    
    def __init__(self, context):
        super(Referenced, self).__init__(context)
        self._index = dict()
        self._uuid = None
        self.uuid = uuid.uuid4()
    
    def _get_uuid(self):
        return self._uuid

    def _set_uuid(self, uuid):
        iuuid = uuid is not None and int(uuid) or None
        if self._index is not None \
          and iuuid in self._index \
          and self._index[iuuid] is not self:
            raise ValueError, u"Given uuid was already used for another Node"
        siuuid = self._uuid is not None and int(self._uuid) or None
        if self._index is not None and siuuid in self._index:
            del self._index[siuuid]
        if self._index is not None:
            self._index[iuuid] = self
        self._uuid = uuid

    uuid = property(_get_uuid, _set_uuid)
    
    @property
    def index(self):
        return NodeIndex(self._index)
    
    def node(self, uuid):
        return self._index.get(int(uuid))
    
    @before('__setitem__')
    def before_setitem(self, key, val):
        try:
            # remember val __name__ and __parent__ for reverting
            old__name__ = val.__name__
            old__parent__ = val.__parent__
        except AttributeError:
            # nothing to index
            return
        # immediately set __name__ and __parent__ on val, implementation often
        # require hierarchy information to acquire keys
        val.__name__ = key
        val.__parent__ = self.context.context
        has_children = False
        for valkey in val.iterkeys():
            has_children = True
            break
        if has_children:
            keys = set(self._index.keys())
            if keys.intersection(val._index.keys()):
                val.__name__ = old__name__
                val.__parent__ = old__parent__
                raise ValueError, u"Node with uuid already exists"
        self._index.update(val._index)
        val._alter_node_index(self._index)
    
    @before('__delitem__')
    def before_delitem(self, key):
        for iuuid in self.context[key]._to_delete():
            del self._index[iuuid]
    
    def _alter_node_index(self, index):
        self._index = index
    
    def _to_delete(self):
        todel = [int(self.uuid)]
        for childkey in self.context:
            try:
                todel += self.context[childkey]._to_delete()
            except AttributeError:
                # Non-Node values are not told about deletion
                continue
        return todel