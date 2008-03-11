import sys, math
from cctbx.array_family import flex
from mmtbx import find_peaks
from mmtbx import utils
import iotbx.phil
from scitbx import matrix
from libtbx import adopt_init_args
from mmtbx.refinement import print_statistics
import mmtbx.utils

master_params_part1 = iotbx.phil.parse("""\
map_type = mFobs-DFmodel
  .type = str
  .help = Map type to be used to find hydrogens
map_cutoff = 2.0
  .type = float
  .help = Map cutoff
angular_step = 3.0
  .type = float
  .help = Step in degrees for 6D rigid body search for best fit
""")

master_params_part2 = find_peaks.master_params.fetch(iotbx.phil.parse("""\
use_sigma_scaled_maps = True
resolution_factor = 1./4.
map_next_to_model
{
  min_model_peak_dist = 0.7
  max_model_peak_dist = 1.05
  min_peak_peak_dist = 1.0
  use_hydrogens = False
}
peak_search
{
  peak_search_level = 1
  min_cross_distance = 1.0
}
"""))

def all_master_params():
  return iotbx.phil.parse("""\
    include scope mmtbx.hydrogens.find.master_params_part1
    include scope mmtbx.hydrogens.find.master_params_part2
""", process_includes=True)

class h_peak(object):
  def __init__(self, site_frac,
                     height,
                     dist,
                     scatterer_o,
                     atom_attribute_o,
                     i_seq_o):
    self.site_frac        = site_frac
    self.height           = height
    self.dist             = dist
    self.scatterer_o      = scatterer_o
    self.atom_attribute_o = atom_attribute_o
    self.i_seq_o          = i_seq_o

class water_and_peaks(object):
  def __init__(self, i_seq_o,
                     i_seq_h1,
                     i_seq_h2,
                     peaks_sites_frac):
    assert [i_seq_o,i_seq_h1,i_seq_h2,peaks_sites_frac].count(None) == 0
    adopt_init_args(self, locals())

def water_bond_angle(o,h1,h2):
  result = None
  a = h1[0]-o[0], h1[1]-o[1], h1[2]-o[2]
  b = h2[0]-o[0], h2[1]-o[1], h2[2]-o[2]
  a = matrix.col(a)
  b = matrix.col(b)
  return a.angle(b, deg=True)

def find_hydrogen_peaks(fmodel,
                        atom_attributes_list,
                        params,
                        log):
  fp_manager = find_peaks.manager(fmodel     = fmodel,
                                  map_type   = params.map_type,
                                  map_cutoff = params.map_cutoff,
                                  params     = params,
                                  log        = log)
  result = fp_manager.peaks_mapped()
  fp_manager.show_mapped(atom_attributes_list = atom_attributes_list)
  return result

def extract_hoh_peaks(peaks, atom_attributes_list, xray_structure, log):
  scatterers = xray_structure.scatterers()
  assert scatterers.size() == len(atom_attributes_list)
  assert peaks.sites.size() == peaks.heights.size()
  assert peaks.heights.size() == peaks.iseqs_of_closest_atoms.size()
  perm = flex.sort_permutation(peaks.iseqs_of_closest_atoms)
  sites = peaks.sites.select(perm)
  heights = peaks.heights.select(perm)
  iseqs_of_closest_atoms = peaks.iseqs_of_closest_atoms.select(perm)
  result = {}
  tmp = []
  unit_cell = xray_structure.unit_cell()
  get_class = iotbx.pdb.common_residue_names_get_class
  for s, h, i_seq in zip(sites, heights, iseqs_of_closest_atoms):
    aa = atom_attributes_list[i_seq]
    assert aa.element.strip() not in ['H','D']
    if(get_class(name = aa.resName) == "common_water"):
      assert aa.element.strip() == 'O'
      result.setdefault(aa, []).append(s)
  waters_and_peaks = []
  for i_seq_o, aa in enumerate(atom_attributes_list):
    if(get_class(name = aa.resName) == "common_water"):
      if(result.has_key(aa)):
        i_seqs_h = []
        for i_seq_h, aa_i in enumerate(atom_attributes_list):
          if(get_class(name = aa_i.resName) == "common_water"):
            if(aa.chainID == aa_i.chainID and
               aa.residue_id() == aa_i.residue_id() and
               aa_i.element.strip() != 'O'):
              i_seqs_h.append(i_seq_h)
        res = water_and_peaks(i_seq_o          = i_seq_o,
                              i_seq_h1         = i_seqs_h[0],
                              i_seq_h2         = i_seqs_h[1],
                              peaks_sites_frac = result[aa])
        waters_and_peaks.append(res)
  return waters_and_peaks

def fit_water(water_and_peaks, xray_structure, params, log):
  scatterers = xray_structure.scatterers()
  uc = xray_structure.unit_cell()
  site_frac_o  = scatterers[water_and_peaks.i_seq_o ].site
  site_frac_h1 = scatterers[water_and_peaks.i_seq_h1].site
  site_frac_h2 = scatterers[water_and_peaks.i_seq_h2].site
  peak_sites_frac = water_and_peaks.peaks_sites_frac
  if(len(peak_sites_frac) == 1):
    result = mmtbx.utils.fit_hoh(
      site_frac_o     = site_frac_o,
      site_frac_h1    = site_frac_h1,
      site_frac_h2    = site_frac_h2,
      site_frac_peak1 = peak_sites_frac[0],
      site_frac_peak2 = peak_sites_frac[0],
      angular_shift   = params.angular_step,
      unit_cell       = uc)
    d_best = result.dist_best()
    o = uc.fractionalize(result.site_cart_o_fitted)
    h1 = uc.fractionalize(result.site_cart_h1_fitted)
    h2 = uc.fractionalize(result.site_cart_h2_fitted)
  else:
    peak_pairs = []
    for i, s1 in enumerate(peak_sites_frac):
      for j, s2 in enumerate(peak_sites_frac):
        if i < j:
          peak_pairs.append([s1,s2])
    d_best = 999.
    for pair in peak_pairs:
      result = mmtbx.utils.fit_hoh(
        site_frac_o     = site_frac_o,
        site_frac_h1    = site_frac_h1,
        site_frac_h2    = site_frac_h2,
        site_frac_peak1 = pair[0],
        site_frac_peak2 = pair[1],
        angular_shift   = params.angular_step,
        unit_cell       = uc)
      if(result.dist_best() < d_best):
        d_best = result.dist_best()
        o = uc.fractionalize(result.site_cart_o_fitted)
        h1 = uc.fractionalize(result.site_cart_h1_fitted)
        h2 = uc.fractionalize(result.site_cart_h2_fitted)
  scatterers[water_and_peaks.i_seq_o ].site = o
  scatterers[water_and_peaks.i_seq_h1].site = h1
  scatterers[water_and_peaks.i_seq_h2].site = h2
  print >> log, "%6.3f"%d_best

def run(fmodel, model, log, params = None):
  print_statistics.make_header("Fit water hydrogens into residual map",
    out = log)
  if(params is None):
    params = all_master_params().extract()
  print_statistics.make_sub_header("find peak-candidates", out = log)
  peaks = find_hydrogen_peaks(
    fmodel               = fmodel,
    atom_attributes_list = model.atom_attributes_list,
    params               = params,
    log                  = log)
  waters_and_peaks = extract_hoh_peaks(
    peaks                = peaks,
    atom_attributes_list = model.atom_attributes_list,
    xray_structure       = model.xray_structure,
    log                  = log)
  print_statistics.make_sub_header("6D rigid body fit of HOH", out = log)
  print >> log, "Fit quality:"
  for water_and_peaks in waters_and_peaks:
    fit_water(water_and_peaks = water_and_peaks,
              xray_structure  = model.xray_structure,
              params          = params,
              log             = log)
