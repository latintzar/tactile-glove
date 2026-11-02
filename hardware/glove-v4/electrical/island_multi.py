"""Use existing connected vias as router endpoints instead of refanning escaped pins."""
import pcbnew as k,math,re
xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));LAYERS=[k.F_Cu,k.In2_Cu,k.In5_Cu,k.B_Cu]
def candidates(b,net,point,allowed):
 from routing_layers import assert_stack
 assert_stack(b)
 seeds=[]
 for f in b.GetFootprints():
  for p in f.Pads():
   if p.GetNetname()==net and math.dist(xy(p.GetPosition()),point)<.0003 and any(p.IsOnLayer(l) for l in allowed):seeds.append(p)
 for t in b.GetTracks():
  if t.GetNetname()!=net:continue
  if type(t)==k.PCB_VIA:
   if math.dist(xy(t.GetPosition()),point)<.0003:seeds.append(t)
  elif t.GetLayer() in allowed and (math.dist(xy(t.GetStart()),point)<.0003 or math.dist(xy(t.GetEnd()),point)<.0003):seeds.append(t)
 c=b.GetConnectivity();queue=list(seeds);seen=set();vias=[];tracks=[];pads=[]
 while queue and len(seen)<600:
  i=queue.pop();uid=i.m_Uuid.AsString()
  if uid in seen:continue
  seen.add(uid)
  if i.Type()==k.PCB_VIA_T:vias.append(xy(i.GetPosition()))
  elif i.Type()==k.PCB_TRACE_T and i.GetLayer() in LAYERS:
   start=xy(i.GetStart());end=xy(i.GetEnd());n=max(1,int(math.dist(start,end)/.6))
   tracks.extend([((start[0]+(end[0]-start[0])*j/n,start[1]+(end[1]-start[1])*j/n),[i.GetLayer()]) for j in range(n+1)])
  elif i.Type()==k.PCB_PAD_T:pads.append((xy(i.GetPosition()),[l for l in LAYERS if i.IsOnLayer(l)]))
  queue.extend(c.GetConnectedTracks(i));queue.extend(c.GetConnectedPads(i))
 return [(p,LAYERS) for p in set(vias)]+tracks+pads or [(point,allowed)]
