"""Use existing connected vias as router endpoints instead of refanning escaped pins."""
import pcbnew as k,math,re
xy=lambda p:(k.ToMM(p.x),k.ToMM(p.y));LAYERS=[k.F_Cu,k.In2_Cu,k.In5_Cu,k.B_Cu]
def via_candidates(b,net,point,allowed):
 seeds=[]
 for f in b.GetFootprints():
  for p in f.Pads():
   if p.GetNetname()==net and math.dist(xy(p.GetPosition()),point)<.0003 and any(p.IsOnLayer(l) for l in allowed):seeds.append(p)
 for t in b.GetTracks():
  if t.GetNetname()!=net:continue
  if type(t)==k.PCB_VIA:
   if math.dist(xy(t.GetPosition()),point)<.0003:seeds.append(t)
  elif t.GetLayer() in allowed and (math.dist(xy(t.GetStart()),point)<.0003 or math.dist(xy(t.GetEnd()),point)<.0003):seeds.append(t)
 c=b.GetConnectivity();queue=list(seeds);seen=set();vias=[]
 while queue and len(seen)<600:
  i=queue.pop();uid=i.m_Uuid.AsString()
  if uid in seen:continue
  seen.add(uid)
  if i.Type()==k.PCB_VIA_T:vias.append(xy(i.GetPosition()))
  queue.extend(c.GetConnectedTracks(i));queue.extend(c.GetConnectedPads(i))
 return [(p,LAYERS) for p in sorted(set(vias),key=lambda p:math.dist(p,point))[:40]]
def choose(b,net,a,d):
 b.BuildConnectivity();aa=via_candidates(b,net,*a);dd=via_candidates(b,net,*d)
 if not aa:aa=[a]
 if not dd:dd=[d]
 return min(((math.dist(x[0],y[0]),x,y) for x in aa for y in dd),key=lambda t:t[0])[1:]
