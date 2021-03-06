# -*- coding: utf-8 -*-
"""
This library is an __.

:authors: John Byaka
:copyright: Copyright 2019, Buber
:license: Apache License 2.0

:license:

   Copyright 2019 Buber

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from .utils import *
from .DBTestBase import *
from .DBBase import DBBase
from .DBBase import __version__ as VERSION
from .extensions import extensions
from . import errors

DBExts=MagicDict({})
DBExtsMap={}
for n, m in extensions.iteritems():
   if not hasattr(m, '__init'):
      print 'WARNING: db.extension.%s missing init statement, skipped'%n
      continue
   o, alias=m.__init()
   alias=[s.lower() for s in ([alias] if isString(alias) else alias)]
   DBExts[o.__name__]=o
   DBExtsMap[o]={'alias':alias, 'module':m, 'errors':{}}
   for s in alias: DBExts[s]=o
   for k in dir(m):
      try:
         oo=getattr(m, k)
         assert issubclass(oo, Exception)
         assert oo.__module__==o.__module__
         DBExtsMap[o]['errors'][k]=oo
      except Exception: pass

def VombatiDB(exts):
   if exts:
      tArr=list(exts) if (isList(exts) or isTuple(exts)) else [exts]
      exts=[]
      for o in tArr:
         if isString(o):
            o=o.lower()
            if o not in DBExts:
               raise ValueError('Unknow db-extension "%s"'%o)
            o=DBExts[o]
         if not issubclass(o, DBBase):
            raise ValueError('Passed db-extension must be a sub-class of DBBase')
         exts.append(o)
      # checking dependences
      extsMap=dict((o.__name__, i) for i, o in enumerate(exts))
      for extI, o in enumerate(exts):
         depMap=getattr(o, '_%s__depend'%o.__name__, None)
         if not depMap: continue
         for oo in depMap:
            if not oo: continue
            oo=oo if isTuple(oo) or isList(oo) else [oo]
            for oo2 in oo:
               isUnordered, depName=(True, oo2[1:]) if oo2[0]=='~' else (False, oo2)
               depO=DBExts[depName]
               if depO in extsMap and (isUnordered or extI>extsMap[depO]): break
            else:
               continue
            s=oo[0] if len(oo)==1 else ' or '.join(oo)
            raise ExtensionDependencyError('%s need %s'%(o.__name__, s))
      # import errors
      for o in exts:
         for k,v in DBExtsMap[o]['errors'].iteritems():
            setattr(errors, k, v)
   print 'Creating DB-instance '+'[%s] '%VERSION+('(original)' if not exts else 'with exts: %s'%', '.join(o.__name__ for o in exts))+'.'
   return ClassFactory(DBBase, exts, fixPrivateAttrs=True)
