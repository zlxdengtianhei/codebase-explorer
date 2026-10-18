"""Audit persisted credentials, with narrow AST exceptions for public identifiers."""
import ast,gzip,os,shutil
from pathlib import Path

def audited_public_matches(path,data,key):
 if key not in data:return []
 assert path.suffix=='.py' and path.name in {'gateway.py','finalize.py'},str(path)
 text=data.decode();tree=ast.parse(text);parents={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)};lines=data.splitlines(keepends=True);spans=[];records=[]
 for node in ast.walk(tree):
  if not isinstance(node,ast.Constant) or not isinstance(node.value,str) or key.decode() not in node.value:continue
  assert node.value==key.decode(),str(path)
  parent=parents.get(node);reason=None
  if path.name=='gateway.py' and isinstance(parent,ast.List) and parent.elts[0] is node:
   call=parents.get(parent)
   if isinstance(call,ast.Call) and call.args and call.args[0] is parent and isinstance(call.func,ast.Attribute) and isinstance(call.func.value,ast.Name) and call.func.value.id=='subprocess' and call.func.attr=='run' and len(parent.elts)>1 and isinstance(parent.elts[1],ast.Constant) and parent.elts[1].value=='usage' and shutil.which(node.value):reason='Installed public CLI executable, not a credential argument'
  if path.name=='finalize.py' and isinstance(parent,ast.Subscript) and parent.slice is node and isinstance(parent.value,ast.Subscript) and isinstance(parent.value.slice,ast.Constant) and parent.value.slice.value=='providers':reason='Public provider dictionary key, not apiKey value'
  assert reason,str(path)
  start=sum(map(len,lines[:node.lineno-1]))+node.col_offset;end=sum(map(len,lines[:node.end_lineno-1]))+node.end_col_offset
  spans.append((start,end));records.append({'file':path.name,'line':node.lineno,'context':reason})
 start=0
 while True:
  at=data.find(key,start)
  if at<0:break
  assert any(lo<=at and at+len(key)<=hi for lo,hi in spans),str(path)
  start=at+len(key)
 return records

def scan(root,key):
 count=0;exceptions=[]
 for base,dirs,files in os.walk(root,followlinks=False):
  dirs[:]=[d for d in dirs if d not in {'arms','harness','venv','cbe-venv','__pycache__'}]
  for name in files:
   p=Path(base)/name
   if p.is_symlink():continue
   data=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
   exceptions.extend(audited_public_matches(p,data,key));count+=1
 return {'files_scanned':count,'credential_values_persisted':False,'public_identifier_exceptions':exceptions,'rule':'Every configured-value byte match must be an audited installed-CLI executable or provider dictionary key; credential assignments, JSON values, authorization headers and all other contexts fail'}
