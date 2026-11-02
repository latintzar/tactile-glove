"""Canonical eight-layer routing contract. Refuse silently misnamed layers."""
import pcbnew as k
SIGNAL_LAYERS=[k.F_Cu,k.In2_Cu,k.In5_Cu,k.B_Cu]
ALL_COPPER=[k.F_Cu,k.In1_Cu,k.In2_Cu,k.In3_Cu,k.In4_Cu,k.In5_Cu,k.In6_Cu,k.B_Cu]
def assert_stack(board):
 assert board.GetCopperLayerCount()==8,'Current helpers require the verified eight-layer board'
 for layer,name in [(k.In1_Cu,'GND_TOP'),(k.In2_Cu,'SIGNAL_TOP'),(k.In3_Cu,'POWER_A'),(k.In4_Cu,'POWER_B'),(k.In5_Cu,'SIGNAL_BOTTOM'),(k.In6_Cu,'GND_BOTTOM')]:
  assert board.GetLayerName(layer)==name,(layer,board.GetLayerName(layer),name)
 return SIGNAL_LAYERS
