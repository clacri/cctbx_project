# $Id$

import sys
import sgtbx

def parse(hall_symbol):
  s = sgtbx.parse_string(hall_symbol)
  try:
    return sgtbx.SpaceGroup(s)
  except RuntimeError, e:
    print "-->" + s.string() + "<--"
    print ("-" * (s.where() + 3)) + "^"
    print e.args[0]
    return None

def show(SgOps):
  print "nLTr:", SgOps.nLTr();
  print "fInv:", SgOps.fInv();
  print "nSMx:", SgOps.nSMx();
  for iLIS in xrange(SgOps.OrderZ()):
    print SgOps(iLIS).as_xyz()

def show_RotMxInfo(SgOps):
  for iLIS in xrange(SgOps.OrderZ()):
    info = SgOps(iLIS).getRotMxInfo()
    print "Rtype =", info.Rtype(),
    print "EV =", info.EV(),
    print "SenseOfRotation =", info.SenseOfRotation()

def hkl(SgOps):
  H = (1,2,-3)
  semi = SgOps.getEquivMillerIndices(H)
  for iList in xrange(semi.M(0)):
    print semi(iList)
  for iList in xrange(semi.N()):
    print semi[iList].HR(), semi[iList].HT()
  CutP = SgOps.getCutParameters()
  print 'CutParameters =', CutP
  Master = SgOps.getMasterIndex(H, CutP, 1)
  print Master.H()
  print Master.iMate()
  for Pretty in xrange(2):
    Master = SgOps.getMasterIndex(H, CutP, Pretty)
    for iList in xrange(semi.M(0)):
      assert(Master.H() == SgOps.getMasterIndex(semi(iList), CutP, Pretty).H())

def BuildIndices(SgOps):
  import uctbx
  UnitCell = uctbx.UnitCell((10, 10, 10, 90, 90, 90))
  MIG = sgtbx.MillerIndexGenerator(UnitCell, SgOps, 3)
  print MIG.ASU().ReferenceASU().representation()
  for H in MIG: print H

if (__name__ == '__main__'):
  SgOps = parse(sys.argv[1])
  if (SgOps):
    show(SgOps)
    #show_RotMxInfo(SgOps)
    #hkl(SgOps)
    BuildIndices(SgOps)
