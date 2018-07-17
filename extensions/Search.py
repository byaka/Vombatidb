# -*- coding: utf-8 -*-
from ..utils import *
from ..DBBase import DBBase

try:
   #~ если эта библиотека еще гдето понадобится, нужно перенести ее в `utils.py` и возможно добавить упрощенную встроенную реализацию
   from lru import LRU as lruDict
except ImportError:
   global lruDict
   lruDict=False

def __init():
   return DBSearch_simple, ('Search', 'Query')

class QueryError(BaseDBErrorPrefixed):
   """Error occured while processing query"""

class DBSearch_simple(DBBase):
   def _init(self, *args, **kwargs):
      res=super(DBSearch_simple, self)._init(*args, **kwargs)
      self.query_pattern_check_data=re.compile(r'[^\w\d_]+DATA[^\w\d_]+')
      self.query_pattern_check_ns=re.compile(r'[^\w\d_]+NS|INDEX[^\w\d_]+')
      self.query_pattern_clear_indent=re.compile(r'^ {6}', re.MULTILINE)
      self.query_pattern_clear_indent2=re.compile(r'^', re.MULTILINE)
      self.query_pattern_globalsRepared='__GLOBALS_REPARED'
      self.query_envName='<DBSearch_simple.query>'
      self.settings.queryCache=1000
      self._queryCache=None
      return res

   def _connect(self, **kwargs):
      if lruDict and self._settings['queryCache']:
         self._queryCache=lruDict(self._settings['queryCache'])
      else:
         self._queryCache=None
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

   def queryPrep(self, what=None, branch=None, where=None, limit=None, pre=None, recursive=True, returnRaw=False, calcProperties=True, precompile=True, allowCache=True):
      stopwatch=self.stopwatch('queryPrep%s@DBSearch_simple'%('-precompile' if precompile else ''))
      _tab=' '*3
      if not what or what=='*': what=None
      elif isinstance(what, (str, unicode, list, tuple)):
         if isinstance(what, (list, tuple)):
            what=', '.join(what)
         what='(%s)'%what
      else:
         raise ValueError('Incorrect type for `branch` arg')
      if not branch: branch=None
      elif isinstance(branch, (str, unicode, list, tuple)):
         branch=self._prepIds(branch)
      else:
         raise ValueError('Incorrect type for `branch` arg')
      if not where: where=None
      elif isinstance(where, (str, unicode, list, tuple)):
         if isinstance(where, (list, tuple)):
            where=' and '.join(where)
         where='not(%s)'%where
      else:
         raise ValueError('Incorrect type for `where` arg')
      if not pre: pre=''
      elif isinstance(pre, (str, unicode, list, tuple)):
         if isinstance(pre, (list, tuple)):
            pre='\n'.join(pre)
         pre='# pre-processing begin\n%s\n# pre-processing end'%pre
         pre='\n'+self.query_pattern_clear_indent2.sub(_tab*4, pre)
      else:
         raise ValueError('Incorrect type for `pre` arg')
      #
      qId=(branch, where, what, limit, recursive, returnRaw, calcProperties)
      if allowCache and self._queryCache is not None and qId in self._queryCache:
         stopwatch()
         return self._queryCache[qId]
      #
      qRaw=repr({
         'what':what,
         'branch':branch,
         'where':where,
         'limit':limit,
         'pre':pre,
         'recursive':recursive,
         'returnRaw':returnRaw,
         'calcProperties':calcProperties,
      })
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
      _return_template=what or ('IDS, (PROPS, DATA, CHILDS)' if _data_need1 else 'IDS, (PROPS, CHILDS)')
      code=["""
      def RUN():
         try:"""+pre+"""
            db_parseId2NS=DB._parseId2NS
            db_get=DB.get
            _MagicDict=MagicDict
            _StrictModeError=StrictModeError
            c=0
            g=DB.iterIndex(%s, recursive=%s, calcProperties=%s, treeMode=False, safeMode=True)
            for IDS, (PROPS, CHILDS) in g:
               ID=IDS[-1]"""%(branch, recursive, calcProperties)]
      _code=code.append
      _indent1=_tab*5
      if _ns_need1:
         _code(_indent1+"NS, INDEX=db_parseId2NS(ID)")
      if _data_need1:
         _code(_indent1+"try: DATA=db_get(IDS, existChecked=PROPS, returnRaw=%s, strictMode=True)"%(returnRaw))
         _code(_indent1+"except _StrictModeError: continue")
      if where:
         _code(_indent1+"if %s: continue  # WHERE-condition"%where)
      if not _ns_need1 and _ns_need2:
         _code(_indent1+"NS, INDEX=db_parseId2NS(ID)")
      if not _data_need1 and _data_need2:
         _code(_indent1+"try: DATA=db_get(IDS, existChecked=PROPS, returnRaw=%s, strictMode=True)"%(returnRaw))
         _code(_indent1+"except _StrictModeError: continue")
      if not returnRaw:
         _code(_indent1+"PROPS=_MagicDict(PROPS)")
      if limit==1:
         _code(_indent1+"return "+_return_template)
      else:
         _code(_indent1+"extCmd=yield "+_return_template)
         _code(_indent1+"c+=1")
         if limit:
            _code(_indent1+"if c>=%i: break"%limit)
         _code(_indent1+"if extCmd is not None:")
         _code(_indent1+_tab+"yield")
         _code(_indent1+_tab+"g.send(extCmd)")
      _code(_tab*3+"except Exception: __QUERY_ERROR_HANDLER(RUN.source, %s)"%qRaw)
      _code("RUN.query=%s"%qRaw)
      _code("RUN.dump=lambda: '''%s'''"%qRaw)
      #
      code='\n'.join(code)
      code=self.query_pattern_clear_indent.sub('', code.strip('\n'))
      # fileWrite(getScriptPath()+'/q_compiled.py', code)
      if precompile:
         code+='\nRUN.source="""%s"""'%code
         code=compile(code, self.query_envName, 'exec')
      if allowCache:
         self._queryCache[qId]=code
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
         env=self._main_app.__dict__
      elif isinstance(env, dict):
         pass
      else:
         raise ValueError('Incorrect type for `env` arg')
      #
      if not qIsF:
         tArr=env.copy()
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
         qArr[eLine-lineOffset]='>>'+qArr[eLine-lineOffset][2:]
         eObj='%s at line %i: %s'%(type(eObj).__name__, eLine, eObj)
      else:
         eSource2, eLine2, eObj2, _=traceback.extract_tb(eTB)[0]
         if eSource2==self.query_envName:
            qArr[eLine2-lineOffset]='>>'+qArr[eLine2-lineOffset][2:]
         eObj='%s%s: %s'%(''.join(traceback.format_tb(eTB)), type(eObj).__name__, eObj)
      q='\n'.join(qArr)
      res+='\n'+'-'*40+'\n'
      res+=q
      res+='\n'+'-'*40+'\n'
      res+=eObj
      raise QueryError(res)
