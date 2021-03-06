"Please help adding characters commonly used in science."
from __future__ import division

import sys

def run(args):
  assert len(args) == 0
  unicode_text = u"""
\u00C5 LATIN CAPITAL LETTER A WITH RING ABOVE
\u00B0 DEGREE SIGN
\u0391 GREEK CAPITAL LETTER ALPHA
\u0392 GREEK CAPITAL LETTER BETA
\u0393 GREEK CAPITAL LETTER GAMMA = gamma function
\u0394 GREEK CAPITAL LETTER DELTA
\u0395 GREEK CAPITAL LETTER EPSILON
\u0396 GREEK CAPITAL LETTER ZETA
\u0397 GREEK CAPITAL LETTER ETA
\u0398 GREEK CAPITAL LETTER THETA
\u0399 GREEK CAPITAL LETTER IOTA = iota adscript
\u039A GREEK CAPITAL LETTER KAPPA
\u039B GREEK CAPITAL LETTER LAMDA
\u039C GREEK CAPITAL LETTER MU
\u039D GREEK CAPITAL LETTER NU
\u039E GREEK CAPITAL LETTER XI
\u039F GREEK CAPITAL LETTER OMICRON
\u03A0 GREEK CAPITAL LETTER PI
\u03A1 GREEK CAPITAL LETTER RHO
\u03A3 GREEK CAPITAL LETTER SIGMA
\u03A4 GREEK CAPITAL LETTER TAU
\u03A5 GREEK CAPITAL LETTER UPSILON
\u03A6 GREEK CAPITAL LETTER PHI
\u03A7 GREEK CAPITAL LETTER CHI
\u03A8 GREEK CAPITAL LETTER PSI
\u03A9 GREEK CAPITAL LETTER OMEGA
\u03C6 GREEK SMALL LETTER PHI
\u03C7 GREEK SMALL LETTER CHI
\u03C8 GREEK SMALL LETTER PSI
\u03C9 GREEK SMALL LETTER OMEGA
\u03B2 greek small letter beta
\u03B8 greek small letter theta
\u03A5 greek capital letter upsilon
\u03C6 greek small letter phi
\u03C0 greek small letter pi
\u03B2 GREEK SMALL LETTER BETA
\u00DF latin small letter sharp s
\u03B3 GREEK SMALL LETTER GAMMA
\u03B4 GREEK SMALL LETTER DELTA
\u03B5 GREEK SMALL LETTER EPSILON
\u03B6 GREEK SMALL LETTER ZETA
\u03B7 GREEK SMALL LETTER ETA
\u03B8 GREEK SMALL LETTER THETA
\u03B9 GREEK SMALL LETTER IOTA
\u03BA GREEK SMALL LETTER KAPPA
\u03BB GREEK SMALL LETTER LAMDA = lambda
\u03BC GREEK SMALL LETTER MU
\u00B5 micro sign
\u03BD GREEK SMALL LETTER NU
\u03BE GREEK SMALL LETTER XI
\u03BF GREEK SMALL LETTER OMICRON
\u03C0 GREEK SMALL LETTER PI math constant 3.141592...
\u03C1 GREEK SMALL LETTER RHO
\u03C2 GREEK SMALL LETTER FINAL SIGMA
\u03C3 GREEK SMALL LETTER SIGMA
\u03C4 GREEK SMALL LETTER TAU
\u03C5 GREEK SMALL LETTER UPSILON
"""
  print unicode_text.encode("utf-8", "strict")

if (__name__ == "__main__"):
  run(args=sys.argv[1:])
