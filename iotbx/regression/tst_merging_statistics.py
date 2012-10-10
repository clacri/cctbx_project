from __future__ import division
import libtbx.load_env
from libtbx.test_utils import approx_equal
from iotbx.command_line import merging_statistics
from cctbx.array_family import flex
import os
import sys
from cStringIO import StringIO

def exercise (debug=False) :
  if (not libtbx.env.has_module("phenix_regression")) :
    print "phenix_regression not configured, skipping."
    return
  hkl_file = libtbx.env.find_in_repositories(
    relative_path="phenix_regression/wizards/p9_se_w2.sca",
    test=os.path.isfile)
  args = [
    hkl_file,
    "space_group=I4",
    "unit_cell=113.949,113.949,32.474,90,90,90",
    "loggraph=True",
  ]
  if (debug) :
    args.append("debug=True")
    print " ".join(args)
  out = StringIO()
  result = merging_statistics.run(args, out=out)
  assert ("R-merge: 0.073" in out.getvalue())
  assert ("R-meas:  0.079" in out.getvalue())
  cif_block = result.as_cif_block()
  assert "_reflns_shell" in cif_block
  assert approx_equal(float(cif_block["_reflns.pdbx_Rpim_I_all"]), 0.0295498162694)
  assert approx_equal(
    flex.int(cif_block["_reflns_shell.number_measured_all"]),
    [15737, 15728, 15668, 15371, 14996, 14771, 13899, 13549, 13206, 12528])

if (__name__ == "__main__") :
  exercise(debug=("--debug" in sys.argv))
  print "OK"
