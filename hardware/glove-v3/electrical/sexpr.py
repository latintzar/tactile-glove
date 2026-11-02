"""Minimal read-only KiCad S-expression parser; preserves quoted tokens."""
import re,json
def parse(s):
 tokens=re.findall(r'"(?:\\.|[^"\\])*"|[^\s()]+|[()]',s);stack=[];root=None
 for t in tokens:
  if t=='(':
   n=[]
   if stack:stack[-1].append(n)
   else:root=n
   stack.append(n)
  elif t==')':stack.pop()
  else:stack[-1].append(t)
 if stack:raise ValueError('unclosed expression')
 return root
def child(n,k):return next((x for x in n if isinstance(x,list) and x[0]==k),None)
def children(n,k):return [x for x in n if isinstance(x,list) and x[0]==k]
def atom(s):return json.loads(s) if s.startswith('"') else s
