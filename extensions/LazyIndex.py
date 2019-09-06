# -*- coding: utf-8 -*-
__ver_major__ = 0
__ver_minor__ = 3
__ver_patch__ = 0
__ver_sub__ = "dev"
__version__ = "%d.%d.%d" % (__ver_major__, __ver_minor__, __ver_patch__)
"""
:authors: John Byaka
:copyright: Copyright 2019, BYaka
:license: Apache License 2.0

:license:

   Copyright 2019 BYaka

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from ..utils import *
from ..DBBase import DBBase

def __init():
   return DBLazyIndex, ('LazyIndex',)

class LazyChilds(DictInterface):
   def __init__(self, mapping=(), cb=None, auto_lazy=False, **kwargs):
      self.__store=dict(mapping, **kwargs)
      self.__cb=None if not callable(cb) else cb
      self.__auto_lazy=auto_lazy

   def __unlazy_props(self, k, v):
      _props, _node=self[k]
      if _props is v or (_props is None and not v): return
      props, node=v, _node
      self[k]=(props, node)

   def __unlazy_node(self, k, v):
      _props, _node=self[k]
      if _node is v or (_node is None and not v): return
      props, node=_props, v
      self[k]=(props, node)

   def __getitem__(self, k):
      props, node=self.__store[k]
      auto_lazy=self.auto_lazy
      if props is None:
         props=LazyChilds(auto_lazy=auto_lazy, cb=self.__unlazy_props)
      if node is None:
         node=LazyChilds(auto_lazy=auto_lazy, cb=self.__unlazy_node)
      return props, node

   def __setitem__(self, k, (props, node)):
      auto_lazy=self.auto_lazy
      if props:
         props=props if isinstance(props, LazyChilds) else LazyChilds(props, auto_lazy=auto_lazy, cb=auto_lazy and self.__unlazy_props)
      else: props=None
      if node:
         node=node if isinstance(node, LazyChilds) else LazyChilds(node, auto_lazy=auto_lazy, cb=auto_lazy and self.__unlazy_node)
      else: node=None
      v=(props, node)
      self.__store[k]=v
      if self.__cb is not None:
         self.__cb(k, v)
         if not self.__auto_lazy: self.__cb=None

   def __delitem__(self, k):
      del self.__store[k]
      if self.__cb is not None:
         self.__cb(k, None)
         if not self.__auto_lazy: self.__cb=None

   def __contains__(self, k):
      return k in self.__store

class LazyChildsAuto(DictInterface):
   def __init__(self, mapping=(), cb=None, **kwargs):
      super(LazyChildsAuto, self).__init__(mapping=(), auto_lazy=True, cb=None, **kwargs)

class DBLazyIndex(DBBase):
   def _init(self, *args, **kwargs):
      res=super(DBLazyIndex, self)._init(*args, **kwargs)
      #! добавить конфигурирование `auto_lazy` для класса (или выбор между `LazyChildsAuto` и `LazyChilds`)
      self.___indexNodeClass=LazyChilds
      self.supports.lazyIndex=True
      return res