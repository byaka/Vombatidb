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

import textwrap

def __init():
   return DBSearch_simple, ('Search', 'Query')

class QueryError(BaseDBErrorPrefixed):
   """Error occured while processing query"""

class DBSearch_simple(DBBase):
   def _init(self, *args, **kwargs):
      res=super(DBSearch_simple, self)._init(*args, **kwargs)
      self.query_pattern_check_what=re.compile(r'[^\w\d_]+WHAT[^\w\d_]+')
      self.query_pattern_check_where=re.compile(r'[^\w\d_]+WHERE[^\w\d_]+')
      self.query_pattern_check_data=re.compile(r'[^\w\d_]+DATA[^\w\d_]+')
      self.query_pattern_check_ns=re.compile(r'[^\w\d_]+NS|INDEX[^\w\d_]+')
      self.query_pattern_globalsRepared='__GLOBALS_REPARED'
      self.query_envName='<DBSearch_simple.query>'
      self.settings.search_queryCache=1000
      self.supports.query=True
      self.supports.search_simple=True
      self.__queryCache=None
      return res

   def _connect(self, **kwargs):
      if lruDict and self._settings['search_queryCache']:
         self.__queryCache=lruDict(self._settings['search_queryCache'])
      else:
         self.workspace.log((2 if self._settings['search_queryCache'] else 3), 'Module `lru` not founded, query-cache switched to unlimited')
         self.__queryCache={}
      return super(DBSearch_simple, self)._connect(**kwargs)

   def query(self, what=None, branch=None, where=None, limit=None, pre=None, recursive=True, returnRaw=False, calcProperties=True, env=None, q=None, checkIsEmpty=True, allowCache=True):
      if q is not None and not isinstance(q, (str, unicode, types.CodeType, types.FunctionType)):
         raise ValueError('Incorrect type of query: %r'%(q,))
      if q is None:
         q=self.queryPrep(what=what, branch=branch, where=where, limit=limit, pre=pre, recursive=recursive, returnRaw=returnRaw, calcProperties=calcProperties, precompile=True, allowCache=allowCache)
      qFunc=self.queryCompile(q, env=env)
      #
      res=qFunc()
      if checkIsEmpty and qFunc.query['limit']!=1:
         try:
            res=gExtend((next(res),), res)
         except StopIteration:
            res=()
      return res

   @staticmethod
   def _indentMultilineSource(tab, lines):
      queue=deque((0, s) for s in lines)
      while queue:
         lvl, line=queue.popleft()
         if not line: continue
         elif isinstance(line, (str, unicode)):
            yield (tab*lvl)+line
         else:
            for _line in reversed(line):
               queue.appendleft((lvl+1, _line))
      raise StopIteration

   def queryPrep(self, what=None, branch=None, where=None, limit=None, pre=None, recursive=True, returnRaw=False, calcProperties=True, precompile=True, allowCache=True):
      stopwatch=self.stopwatch('queryPrep%s@DBSearch_simple'%('-precompile' if precompile else ''))
      _tab=' '*3
      _tabs=tuple(_tab*(5+i) for i in xrange(4))
      what_isMultiline=False
      where_isMultiline=False
      if not what or what=='*': what=None
      elif isinstance(what, (str, unicode, list, tuple)):
         if isinstance(what, (list, tuple)):
            _what=', '.join(what)
            what_isMultiline=self.query_pattern_check_what.search(_what) is not None
            what=_what if not what_isMultiline else ('\n'+_tabs[1])+('\n'+_tabs[1]).join(self._indentMultilineSource(_tab, what))
         else:
            what='(%s)'%what
      else:
         raise ValueError('Incorrect type for `what` arg')
      if not branch: branch=None
      elif isinstance(branch, (str, unicode, list, tuple)):
         branch=self._prepIds(branch)
      else:
         raise ValueError('Incorrect type for `branch` arg')
      if not where: where=None
      elif isinstance(where, (str, unicode, list, tuple)):
         if isinstance(where, (list, tuple)):
            _where=' and '.join(where)
            where_isMultiline=self.query_pattern_check_where.search(_where) is not None
            where=_where if not where_isMultiline else ('\n'+_tabs[1])+('\n'+_tabs[1]).join((self._indentMultilineSource(_tab, where)))
         else:
            where='not(%s)'%where
      else:
         raise ValueError('Incorrect type for `where` arg')
      if not pre: pre=''
      elif isinstance(pre, (str, unicode, list, tuple)):
         if isinstance(pre, (list, tuple)):
            pre=('\n'+_tab*4)+('\n'+_tab*4).join(self._indentMultilineSource(_tab, pre))
         else:
            pre=('\n'+_tab*4)+pre
         pre='\n'+_tab*4+'# PRE-block'+pre+'\n'+_tab*4+'# PRE-block end'
      else:
         raise ValueError('Incorrect type for `pre` arg')
      #
      qId=(branch, where, what, limit, recursive, returnRaw, calcProperties)
      if allowCache and self.__queryCache is not None and qId in self.__queryCache:
         stopwatch()
         return self.__queryCache[qId]
      #
      q={
         'what':what,
         'branch':branch,
         'where':where,
         'limit':limit,
         'pre':pre,
         'recursive':recursive,
         'returnRaw':returnRaw,
         'calcProperties':calcProperties,
      }
      qRaw=repr(q)
      #
      _user_input=''
      if where: _user_input+=where
      if pre: _user_input+=pre
      if _user_input:
         _data_need1=self.query_pattern_check_data.search(_user_input) is not None
         _ns_need1=self.query_pattern_check_ns.search(_user_input) is not None
         if _ns_need1 and not self._supports['namespaces']:
            raise ValueError("You can't use `NS` or `INDEX` in query, missed extension DBNamespaced")
      else:
         _data_need1, _ns_need1=False, False
      _data_need2=_data_need1 or (what and self.query_pattern_check_data.search(what) is not None)
      _ns_need2=_ns_need1 or (what and self.query_pattern_check_ns.search(what) is not None)
      #
      if not what:
         if _data_need1 and _ns_need1:
            what='IDS, (NS, INDEX, PROPS, DATA, CHILDS)'
         elif _data_need1:
            what='IDS, (PROPS, DATA, CHILDS)'
         elif _ns_need1:
            what='IDS, (NS, INDEX, PROPS, CHILDS)'
         else:
            what='IDS, (PROPS, CHILDS)'
      code=["""
         def RUN():
            try:"""+pre+"""
               db_parseId2NS=DB._parseId2NS
               db_get=DB.get
               db_getBacklinks=DB.getBacklinks
               db_iterBacklinks=DB.iterBacklinks
               _MagicDict=MagicDict
               _StrictModeError=StrictModeError
               c=0
               g=DB.iterBranch(%s, recursive=%s, calcProperties=%s, treeMode=False, safeMode=True, returnParent=True)
               for (IDS_PARENT, (PROPS_PARENT, CHILDS_PARENT)), (IDS, (PROPS, CHILDS)) in g:
                  ID=IDS[-1]"""%(branch, recursive, calcProperties)]
      _code=code.append
      if _ns_need1:
         _code(_tabs[1]+"NS, INDEX=db_parseId2NS(ID)")
      if _data_need1:
         _code(_tabs[1]+"try: DATA=db_get(IDS, existChecked=PROPS, returnRaw=%s, strictMode=True)"%(returnRaw))
         _code(_tabs[1]+"except _StrictModeError: continue")
      if where:
         if where_isMultiline:
            _code(_tabs[1]+'# WHERE-block'+where)
            _code(_tabs[1]+"if not(WHERE): continue\n"+_tabs[1]+'# WHERE-block ended')
         else:
            _code(_tabs[1]+"if %s: continue  # WHERE-condition"%where)
      #! нужно проверять, используются ли NS, INDEX или DATA внутри блока `WHERE` и менять местами блоки если да
      if not _ns_need1 and _ns_need2:
         _code(_tabs[1]+"NS, INDEX=db_parseId2NS(ID)")
      if not _data_need1 and _data_need2:
         _code(_tabs[1]+"try: DATA=db_get(IDS, existChecked=PROPS, returnRaw=%s, strictMode=True)"%(returnRaw))
         _code(_tabs[1]+"except _StrictModeError: continue")
      if not returnRaw:  #! нужно проверять, используется ли PROPS
         _code(_tabs[1]+"PROPS=_MagicDict(PROPS)")
      if limit==1:
         if what_isMultiline:
            _code(_tabs[1]+'# WHAT-block'+what)
            _code(_tabs[1]+"return WHAT\n"+_tabs[1]+'# WHAT-block ended')
         else:
            _code(_tabs[1]+"return "+what)
      else:
         if what_isMultiline:
            _code(_tabs[1]+'# WHAT-block'+what)
            _code(_tabs[1]+"extCmd=yield WHAT\n"+_tabs[1]+'# WHAT-block ended')
         else:
            _code(_tabs[1]+"extCmd=yield "+what)
         _code(_tabs[1]+"c+=1")
         if limit:
            _code(_tabs[1]+"if c>=%i: break"%limit)
         _code(_tabs[1]+"if extCmd is not None:")
         _code(_tabs[2]+"yield")
         _code(_tabs[2]+"g.send(extCmd)")
      _code("""
            except Exception: __QUERY_ERROR_HANDLER(RUN.source, RUN.query)
         RUN.query=%s
      """%qRaw)
      #
      code='\n'.join(code)
      code=textwrap.dedent(code)
      # fileWrite('q_compiled.py', code.encode('utf-8'))
      if precompile:
         _code=code
         code+='\nRUN.source="""%s"""'%code
         try:
            code=compile(code, self.query_envName, 'exec')
         except Exception:
            self._queryErrorHandler(_code, q)
      if allowCache:
         self.__queryCache[qId]=code
      stopwatch()
      return code

   def queryCompile(self, q=None, env=None):
      stopwatch=self.stopwatch('queryCompile@DBSearch_simple')
      if isinstance(q, (str, unicode, types.CodeType)):
         qIsF, qFunc, q=False, None, q
      elif isinstance(q, types.FunctionType):
         qIsF, qFunc, q=True, q, q.func_globals['__QUERY_SOURCE']
      else:
         raise ValueError('Incorrect type of query: %r'%(q,))
      if env is None:
         env={}
      elif env is True:
         env=self._main_app.__dict__.copy()
      elif isinstance(env, dict):
         env=env.copy()
      else:
         raise ValueError('Incorrect type for `env` arg')
      #
      if not qIsF:
         tArr=env
      else:
         tArr=qFunc.func_globals
         tArr.update(env)
      tArr['__QUERY_SOURCE']=q
      tArr['__QUERY_ERROR_HANDLER']=self._queryErrorHandler
      tArr['DB']=self
      tArr['MagicDict']=MagicDict
      tArr[self.query_pattern_globalsRepared]=False
      tArr['StrictModeError']=StrictModeError
      if not qIsF:
         exec q in tArr
         qFunc=tArr['RUN']
      stopwatch()
      return qFunc

   def _queryErrorHandler(self, q, qRaw):
      res='\n%r'%qRaw
      eSource, eLine, eObj, eTB=getErrorInfo(raw=True)
      qArr, lineOffset=q.split('\n')[3:-3], 4
      if eSource==self.query_envName:
         s='>>'+qArr[eLine-lineOffset][2:]
         if sys.stdout.isatty():
            s='%s%s%s'%('\x1b[91m', s, '\x1b[0m')
         qArr[eLine-lineOffset]=s
         eObj='%s at line %i: %s'%(type(eObj).__name__, eLine, eObj)
      else:
         eSource2, eLine2, eObj2, _=traceback.extract_tb(eTB)[0]
         if eSource2==self.query_envName:
            s='>>'+qArr[eLine2-lineOffset][2:]
            if sys.stdout.isatty():
               s='%s%s%s'%('\x1b[91m', s, '\x1b[0m')
            qArr[eLine2-lineOffset]=s
         eObj='%s%s: %s'%(''.join(traceback.format_tb(eTB)), type(eObj).__name__, eObj)
      q='\n'.join(qArr)
      res+='\n'+'-'*40+'\n'
      res+=q
      res+='\n'+'-'*40+'\n'
      res+=eObj
      raise QueryError(res)
