from __future__ import division
# LIBTBX_SET_DISPATCHER_NAME phenix.polder
import time
import os, sys
from cStringIO import StringIO
import mmtbx.f_model
import mmtbx.utils
import mmtbx.masks
from mmtbx import map_tools
from iotbx import ccp4_map
from iotbx import file_reader
from iotbx import phil
from iotbx import reflection_file_utils
from iotbx import crystal_symmetry_from_any
import iotbx.pdb
from cctbx import maptbx
from cctbx.array_family import flex
from libtbx.utils import Sorry
from libtbx.utils import multi_out
from libtbx import group_args
from cctbx import miller

legend = """\

Computes omit maps by excluding the bulk solvent in the area around a
selection. One example of application are ligand omit maps. Polder omit maps
can be helpful if the ligand density is weak and obscured by bulk solvent
in conventional omit maps (where the ligand is deleted from the model).

Inputs:
  - File with reflection data (Fobs or Iobs) and R-free flags. It can
    be in most of known formats and spread across multiple files;
  - label(s) selecting which reflection data arrays should be used (in case
    there are multiple choices in input file; otherwise there is no need to
    provide labels);
  - Model file;
  - Atom selection (such as ligand)

Usage examples:
  1. phenix.polder model.cif data.mtz selection="chain A and resseq 1"
  2. phenix.polder model.pdb data.hkl data_labels="FP" selection="chain A"
  3. phenix.polder a.hkl b.hkl model.pdb selection="resseq 435"

Output:
  MTZ file with map coefficients for:
  Polder map:
  - mFo-DFc_polder    : polder difference map coefficients
  - PHImFo-DFc_polder : corresponding phases
  Omit map:
  For this map, the omit selection is deleted from the model and bulk solvent
  enters the area
  - mFo-DFc_omit      : omit difference map coefficients
  - PHImFo-DFc_omit   : corresponding phases

Optional output:
  CCP4 files with mask data:
  - mask_all.ccp4    : mask of original model
  - mask_omit.ccp4   : mask when ligand is omitted
  - mask_polder.ccp4 : mask obtained by polder procedure
"""

master_params_str = """
include scope libtbx.phil.interface.tracking_params
model_file_name = None
  .type = path
  .short_caption = Model file
  .multiple = False
  .help = Model file name
  .style = file_type:pdb bold input_file
solvent_exclusion_mask_selection = None
  .type = str
  .short_caption = Omit selection
  .help = Atoms around which bulk solvent mask is set to zero
  .input_size = 400
reflection_file_name = None
  .type = path
  .short_caption = Data file
  .help = File with experimental data (most of formats: CNS, SHELX, MTZ, etc).
  .style = file_type:hkl bold input_file process_hkl child:fobs:data_labels \
           child:rfree:r_free_flags_labels child:d_min:high_resolution \
           child:d_max:low_resolution
data_labels = None
  .type = str
  .short_caption = Data labels
  .help = Labels for experimental data.
  .style = renderer:draw_fobs_label_widget parent:file_name:reflection_file_name
r_free_flags_labels = None
  .type = str
  .short_caption = Rfree labels
  .help = Labels for free reflections.
  .style = renderer:draw_rfree_label_widget parent:file_name:reflection_file_name
sphere_radius = 5
  .type = float
  .short_caption = Solvent exclusion radius
  .help = Radius of sphere around atoms where solvent mask is reset to zero
high_resolution = None
  .type = float
  .short_caption = High resolution
  .help = High resolution limit
low_resolution = None
  .type = float
  .short_caption = Low resolution
  .help = Low resolution limit
scattering_table = *n_gaussian wk1995 it1992 neutron electron
  .type = choice
  .short_caption = Scattering table
  .help = Scattering table for structure factors calculations
resolution_factor = 0.25
  .type = float
  .short_caption = Resolution factor
  .help = Used to determine the grid step = resolution_factor * high resolution
output_file_name_prefix = None
  .type = str
  .short_caption = Output prefix
  .help = Prefix for output filename
mask_output = False
  .type = bool
  .short_caption = Output masks
  .help = Additional output: ccp4 maps containing the solvent mask for inital \
   model (mask_all.ccp4), when ligand is omitted (mask_omit.ccp4) and the mask \
   used for polder (mask_polder.ccp4).
debug = False
  .type = bool
  .expert_level=3
  .short_caption = Output biased map
  .help = Additional output: biased omit map (ligand used for mask calculation \
   but omitted from model)
gui
  .help = "GUI-specific parameter required for output directory"
{
  output_dir = None
  .type = path
  .style = output_dir
}
"""

master_params = phil.parse(master_params_str, process_includes=True)

def output_map(f_obs, r_free_flags, xray_structure, mask_data, filename, params,
               log):
  f_calc = f_obs.structure_factors_from_scatterers(
    xray_structure = xray_structure).f_calc()
  mask = f_obs.structure_factors_from_map(
    map            = mask_data,
    use_scale      = True,
    anomalous_flag = False,
    use_sg         = False)
  # is it really use_sg = false?
  fmodel = mmtbx.f_model.manager(
    f_obs        = f_obs,
    r_free_flags = r_free_flags,
    f_calc       = f_calc,
    f_mask       = mask)
  fmodel.update_all_scales()
  print >> log, "r_work=%6.4f r_free=%6.4f" % (fmodel.r_work(), fmodel.r_free())
  print >> log, "*"*79
  mc_diff = map_tools.electron_density_map(
    fmodel = fmodel).map_coefficients(
      map_type         = "mFo-DFc",
      isotropize       = True,
      fill_missing     = False)
  if (params.mask_output and filename != 'bias_omit'):
    ccp4_map.write_ccp4_map(
    file_name   = "mask_"+filename+".ccp4",
    unit_cell   = f_obs.unit_cell(),
    space_group = f_obs.space_group(),
    map_data    = mask_data,
    labels      = flex.std_string([""]))
  return mc_diff

def mask_modif(f_obs, mask_data, sites_cart, sphere_radius):
  sel = maptbx.grid_indices_around_sites(
    unit_cell  = f_obs.crystal_symmetry().unit_cell(),
    fft_n_real = mask_data.focus(),
    fft_m_real = mask_data.all(),
    sites_cart = sites_cart,
    site_radii = flex.double(sites_cart.size(), sphere_radius))
  mask = mask_data.as_1d()
  mask.set_selected(sel, 0)
  mask.reshape(mask_data.accessor())
  return mask

def mask_from_xrs_unpadded(xray_structure, n_real):
  mask_params = mmtbx.masks.mask_master_params.extract()
  mask = mmtbx.masks.mask_from_xray_structure(
    xray_structure           = xray_structure,
    p1                       = True,
    shrink_truncation_radius = mask_params.shrink_truncation_radius,
    solvent_radius           = mask_params.solvent_radius,
    for_structure_factors    = True,
    n_real                   = n_real).mask_data
  maptbx.unpad_in_place(map = mask)
  return mask

def compute_polder_map(
  f_obs, r_free_flags, xray_structure, pdb_hierarchy, params, log):
  # output and apply atom selection
  print >> log, "selecting atoms..."
  print >> log, "Selection string:", params.solvent_exclusion_mask_selection
  selection_bool = pdb_hierarchy.atom_selection_cache().selection(
    string = params.solvent_exclusion_mask_selection)
  n_selected = selection_bool.count(True)
  if(n_selected == 0):
    raise Sorry("No atoms where selected. Check selection syntax again.")
  print >> log, "Number of atoms selected:", n_selected
  pdb_hierarchy_selected = pdb_hierarchy.select(selection_bool)
  ligand_str = pdb_hierarchy_selected.as_pdb_string()
  print >> log, "Atoms selected:\n", ligand_str
  # when extracting cartesian coordinates, xray_structure needs to be in P1!
  sites_cart_ligand = xray_structure.select(selection_bool).expand_to_p1(
    sites_mod_positive = True).sites_cart()
  # xray structure object without ligand/selection
  xray_structure_noligand = xray_structure.select(~selection_bool)
  print >> log, "Calculating solvent mask..."
  print >> log, "*"*79
  crystal_gridding = f_obs.crystal_gridding(
    d_min             = f_obs.d_min(),
    symmetry_flags    = maptbx.use_space_group_symmetry,
    resolution_factor = params.resolution_factor)
  # calculate mask using ALL atoms
  mask_data_all = mask_from_xrs_unpadded(
    xray_structure = xray_structure,
    n_real         = crystal_gridding.n_real())
  print >> log, "R factors for unmodified input model and data:"
  mc_diff_all = output_map(
    f_obs          = f_obs,
    r_free_flags   = r_free_flags,
    xray_structure = xray_structure,
    mask_data      = mask_data_all,
    filename       = "all",
    params         = params,
    log            = log)
  #------
  # biased map - for developers
  if (params.debug):
    print >> log, "R factor when ligand is used for mask calculation (biased map):"
    mc_diff_bias_omit = output_map(
      f_obs          = f_obs,
      r_free_flags   = r_free_flags,
      xray_structure = xray_structure_noligand,
      mask_data      = mask_data_all,
      filename       = "bias_omit",
      params         = params,
      log            = log)
  #------
  # compute polder mask
  mask_polder = mask_modif(
    f_obs         = f_obs,
    mask_data     = mask_data_all,
    sites_cart    = sites_cart_ligand,
    sphere_radius = params.sphere_radius)
  print >> log, "R factor for polder map"
  mc_diff_polder = output_map(
    f_obs          = f_obs,
    r_free_flags   = r_free_flags,
    xray_structure = xray_structure_noligand,
    mask_data      = mask_polder,
    filename       = "polder",
    params         = params,
    log            = log)
  # compute mask for structure without ligand
  mask_data_omit = mask_from_xrs_unpadded(
    xray_structure = xray_structure_noligand,
    n_real         = crystal_gridding.n_real())
  print >> log, "R factor when ligand is excluded for mask calculation:"
  mc_diff_omit = output_map(
    f_obs          = f_obs,
    r_free_flags   = r_free_flags,
    xray_structure = xray_structure_noligand,
    mask_data      = mask_data_omit,
    filename       = "omit",
    params         = params,
    log            = log)
  mtz_dataset = mc_diff_polder.as_mtz_dataset(
        column_root_label = "mFo-DFc_polder")
  # add biased map if debug=True
  if (params.debug):
    mtz_dataset.add_miller_array(
      miller_array      = mc_diff_bias_omit,
      column_root_label = "mFo-DFc_bias_omit")
  mtz_dataset.add_miller_array(
    miller_array      = mc_diff_omit,
    column_root_label = "mFo-DFc_omit")
  mtz_object = mtz_dataset.mtz_object()
  polder_file_name = "polder_map_coeffs.mtz"
  if (params.output_file_name_prefix is not None):
    polder_file_name = params.output_file_name_prefix + "_" + polder_file_name
  mtz_object.write(file_name = polder_file_name)
  return group_args(
    xray_structure_noligand = xray_structure_noligand,
    pdb_hierarchy_selected  = pdb_hierarchy_selected,
    crystal_gridding        = crystal_gridding,
    mask_polder             = mask_polder)

# validation for GUI
def validate_params(params):
  if (params.solvent_exclusion_mask_selection is None):
    raise Sorry("No selection for mask calculation found.")
  if (params.sphere_radius < 3):
    raise Sorry("Sphere radius out of range: must be larger than 3 A")
  if (params.model_file_name is None):
    raise Sorry("Model file should be given")
  if (params.reflection_file_name is None):
    raise Sorry("Data file should be given")
  # check if file type is OK
  file_reader.any_file(
    file_name = params.model_file_name).check_file_type(expected_type = 'pdb')
  file_reader.any_file(
    file_name = params.reflection_file_name).check_file_type(
      expected_type = 'hkl')
  if (params.data_labels is None):
    raise Sorry("Data labels should be given")
  if (params.resolution_factor < 0.0):
    raise Sorry(
      "Please use a positive value for the resolution gridding factor.")
  return True

def prepare_f_obs_and_flags(f_obs, r_free_flags):
  sel = f_obs.data()>0
  f_obs = f_obs.select(sel)
  r_free_flags = r_free_flags.select(sel)
  #
  merged = f_obs.as_non_anomalous_array().merge_equivalents()
  f_obs = merged.array().set_observation_type(f_obs)
  #
  merged = r_free_flags.as_non_anomalous_array().merge_equivalents()
  r_free_flags = merged.array().set_observation_type(r_free_flags)
  #
  f_obs, r_free_flags = f_obs.common_sets(r_free_flags)
  return f_obs, r_free_flags

def result_message(cc12, cc13, cc23):
  if (cc13 < 0.7 or
      (cc23 > cc12 and cc23 > cc13) or (cc13 < cc12 and cc13 < cc23)):
    msg = """The polder map is very likely to show bulk-solvent or noise."""
  elif (cc13 >= 0.8):
    msg = 'The polder map is likely to show the ligand.'
  elif (cc13 >= 0.7 and cc13 < 0.8):
    if (cc23 < 0.7*cc13):
      msg = """The polder map is more likely to show ligand than bulk solvent.
But it is recommended to inspect the maps to confirm."""
    else:
      msg = """The polder map is more likely to show bulk-solvent or noise
instead of the ligand. But it is recommended to inspect the maps to confirm."""
  return msg

# parse through command line arguments
def cmd_run(args, validated=False, out=sys.stdout):
  if (len(args) == 0):
    print >> out, "-"*79
    print >> out, "                               phenix.polder"
    print >> out, "-"*79
    print >> out, legend
    print >> out, "-"*79
    master_params.show(out=out)
    return
  log = multi_out()
  log.register("stdout", out)
  log_file_name = "polder.log"
  logfile = open(log_file_name, "w")
  log.register("logfile", logfile)
  print >> log, "phenix.polder is running..."
  print >> log, "input parameters:\n", args
  parsed = master_params
  inputs = mmtbx.utils.process_command_line_args(args = args,
    master_params = parsed,
    suppress_symmetry_related_errors=True)
  #inputs.params.show() #check
  params = inputs.params.extract()
  # check model file
  if len(inputs.pdb_file_names) == 0:
    if (params.model_file_name is None):
      raise Sorry("No model file found.")
  elif (len(inputs.pdb_file_names) == 1):
    params.model_file_name = inputs.pdb_file_names[0]
  else:
    raise Sorry("Only one model file should be given")
  # check reflection file
  reflection_files = inputs.reflection_files
  if (len(reflection_files) == 0):
    if (params.reflection_file_name is None):
      raise Sorry("No reflection file found.")
    else:
      hkl_in = file_reader.any_file(params.reflection_file_name,
        force_type="hkl")
      hkl_in.assert_file_type("hkl")
      reflection_files = [ hkl_in.file_object ]
  # crystal symmetry
  crystal_symmetry = None
  crystal_symmetry = inputs.crystal_symmetry
  if (crystal_symmetry is None):
    crystal_symmetries = []
    for f in [str(params.model_file_name), str(params.reflection_file_name)]:
      cs = crystal_symmetry_from_any.extract_from(f)
      if(cs is not None): crystal_symmetries.append(cs)
    if(len(crystal_symmetries) == 1): crystal_symmetry = crystal_symmetries[0]
    elif(len(crystal_symmetries) == 0):
      raise Sorry("No crystal symmetry found.")
    else:
      if(not crystal_symmetries[0].is_similar_symmetry(crystal_symmetries[1])):
        raise Sorry("Crystal symmetry mismatch between different files.")
      crystal_symmetry = crystal_symmetries[0]
  print >> out, "Working crystal symmetry after inspecting all inputs:"
  crystal_symmetry.show_summary(f=out, prefix="  ")
  f_obs, r_free_flags = None, None
  rfs = reflection_file_utils.reflection_file_server(
    crystal_symmetry = crystal_symmetry,
    force_symmetry   = True,
    reflection_files = reflection_files,
    err              = StringIO())
  parameters = mmtbx.utils.data_and_flags_master_params().extract()
  if (params.data_labels is not None):
    parameters.labels = params.data_labels
  if (params.r_free_flags_labels is not None):
    parameters.r_free_flags.label = params.r_free_flags_labels
  determined_data_and_flags = mmtbx.utils.determine_data_and_flags(
    reflection_file_server = rfs,
    parameters             = parameters,
    keep_going             = True,
    working_point_group = crystal_symmetry.space_group().build_derived_point_group(),
    log                    = StringIO(),
    symmetry_safety_check  = True)
  f_obs = determined_data_and_flags.f_obs
  if (params.data_labels is None):
    params.data_labels = f_obs.info().label_string()
  if (params.reflection_file_name is None):
    params.reflection_file_name = parameters.file_name
  r_free_flags = determined_data_and_flags.r_free_flags
  assert f_obs is not None
  print >> log,  "Input data:"
  print >> log, "  Iobs or Fobs:", f_obs.info().labels
  if (r_free_flags is not None):
    print >> log, "  Free-R flags:", r_free_flags.info().labels
    params.r_free_flags_labels = r_free_flags.info().label_string()
  else:
    print >> log, "  Free-R flags: Not present"
  model_basename = os.path.basename(params.model_file_name.split(".")[0])
  if (len(model_basename) > 0 and
    params.output_file_name_prefix is None):
    params.output_file_name_prefix = model_basename
  print params.output_file_name_prefix
  new_params =  master_params.format(python_object=params)
  new_params.show()
  if (not validated):
    validate_params(params)
  pdb_input = iotbx.pdb.input(file_name = params.model_file_name)
  pdb_hierarchy = pdb_input.construct_hierarchy()
  xray_structure = pdb_hierarchy.extract_xray_structure(
    crystal_symmetry = crystal_symmetry)
  # DON'T USE:
  # xray_structure = pdb_input.xray_structure_simple()
  # atom order might be wrong
  mmtbx.utils.setup_scattering_dictionaries(
    scattering_table = params.scattering_table,
    xray_structure   = xray_structure,
    d_min            = f_obs.d_min())
  #if f_obs is not None:
  f_obs = f_obs.resolution_filter(
    d_min = params.high_resolution,
    d_max = params.low_resolution)
  if (r_free_flags is not None):
    r_free_flags = r_free_flags.resolution_filter(
      d_min = params.high_resolution,
      d_max = params.low_resolution)
# Grab case that data are anomalous
  if (f_obs.anomalous_flag()):
    f_obs, r_free_flags = prepare_f_obs_and_flags(
      f_obs        = f_obs,
      r_free_flags = r_free_flags)
  cpm_obj = compute_polder_map(
    f_obs          = f_obs,
    r_free_flags   = r_free_flags,
    xray_structure = xray_structure,
    pdb_hierarchy  = pdb_hierarchy,
    params         = params,
    log            = log)
# Significance check
  fmodel = mmtbx.f_model.manager(
    f_obs          = f_obs,
    r_free_flags   = r_free_flags,
    xray_structure = xray_structure)
  fmodel.update_all_scales(remove_outliers=False, fast=True)
  f_obs_1 = abs(fmodel.f_model())
  fmodel.update_xray_structure(xray_structure=cpm_obj.xray_structure_noligand,
    update_f_calc=True, update_f_mask=True, force_update_f_mask=True)
  # PVA: do we need it? fmodel.update_all_scales(remove_outliers=False)
  f_obs_2 = abs(fmodel.f_model())
  xrs_selected = cpm_obj.pdb_hierarchy_selected.extract_xray_structure(
    crystal_symmetry = f_obs.crystal_symmetry())
  f_calc = f_obs.structure_factors_from_scatterers(
    xray_structure = cpm_obj.xray_structure_noligand).f_calc()
  f_mask = f_obs.structure_factors_from_map(
    map            = cpm_obj.mask_polder,
    use_scale      = True,
    anomalous_flag = False,
    use_sg         = False)
  def get_poler_diff_map(f_obs):
    fmodel = mmtbx.f_model.manager(
      f_obs        = f_obs,
      r_free_flags = r_free_flags,
      f_calc       = f_calc,
      f_mask       = f_mask)
    fmodel.update_all_scales(remove_outliers=False)
    mc_diff = map_tools.electron_density_map(
      fmodel = fmodel).map_coefficients(
        map_type         = "mFo-DFc",
        isotropize       = True,
        fill_missing     = False)
    fft_map = miller.fft_map(
      crystal_gridding     = cpm_obj.crystal_gridding,
      fourier_coefficients = mc_diff)
    fft_map.apply_sigma_scaling()
    map_data = fft_map.real_map_unpadded()
    return mmtbx.utils.extract_box_around_model_and_map(
      xray_structure = xrs_selected,
      map_data       = map_data,
      box_cushion    = 2.1)
  box_1=get_poler_diff_map(f_obs = f_obs_1)
  box_2=get_poler_diff_map(f_obs = f_obs_2)
  box_3=get_poler_diff_map(f_obs = f_obs)
  sites_cart_box = box_1.xray_structure_box.sites_cart()
  sel = maptbx.grid_indices_around_sites(
    unit_cell  = box_1.xray_structure_box.unit_cell(),
    fft_n_real = box_1.map_box.focus(),
    fft_m_real = box_1.map_box.all(),
    sites_cart = sites_cart_box,
    site_radii = flex.double(sites_cart_box.size(), 2.0))
  b1 = box_1.map_box.select(sel).as_1d()
  b2 = box_2.map_box.select(sel).as_1d()
  b3 = box_3.map_box.select(sel).as_1d()
  print >> log, "Map 1: calculated Fobs with ligand"
  print >> log, "Map 2: calculated Fobs without ligand"
  print >> log, "Map 3: real Fobs data"
  cc12 = flex.linear_correlation(x=b1,y=b2).coefficient()
  cc13 = flex.linear_correlation(x=b1,y=b3).coefficient()
  cc23 = flex.linear_correlation(x=b2,y=b3).coefficient()
  print >>log, "CC(1,2): %6.4f"%cc12
  print >>log, "CC(1,3): %6.4f"%cc13
  print >>log, "CC(2,3): %6.4f"%cc23
  ### D-function
  b1 = maptbx.volume_scale_1d(map=b1, n_bins=10000).map_data()
  b2 = maptbx.volume_scale_1d(map=b2, n_bins=10000).map_data()
  b3 = maptbx.volume_scale_1d(map=b3, n_bins=10000).map_data()
  print >> log, "Peak CC:"
  print >>log, "CC(1,2) peak: %6.4f"%flex.linear_correlation(x=b1,y=b2).coefficient()
  print >>log, "CC(1,3) peak: %6.4f"%flex.linear_correlation(x=b1,y=b3).coefficient()
  print >>log, "CC(2,3) peak: %6.4f"%flex.linear_correlation(x=b2,y=b3).coefficient()
  cutoffs = flex.double(
    [i/10. for i in range(1,10)]+[i/100 for i in range(91,100)])
  d12 = maptbx.discrepancy_function(map_1=b1, map_2=b2, cutoffs=cutoffs)
  d13 = maptbx.discrepancy_function(map_1=b1, map_2=b3, cutoffs=cutoffs)
  d23 = maptbx.discrepancy_function(map_1=b2, map_2=b3, cutoffs=cutoffs)
  print >> log, "q    D(1,2) D(1,3) D(2,3)"
  for c,d12_,d13_,d23_ in zip(cutoffs,d12,d13,d23):
    print >> log, "%4.2f %6.4f %6.4f %6.4f"%(c,d12_,d13_,d23_)
  ###
  if(params.debug):
    box_1.write_ccp4_map(file_name="box_1_polder.ccp4")
    box_2.write_ccp4_map(file_name="box_2_polder.ccp4")
    box_3.write_ccp4_map(file_name="box_3_polder.ccp4")
    cpm_obj.pdb_hierarchy_selected.adopt_xray_structure(
      box_1.xray_structure_box)
    cpm_obj.pdb_hierarchy_selected.write_pdb_file(file_name="box_polder.pdb",
      crystal_symmetry=box_1.box_crystal_symmetry)
  #
  polder_file_name = "polder_map_coeffs.mtz"
  if (params.output_file_name_prefix is not None):
    polder_file_name = params.output_file_name_prefix + "_" + polder_file_name
  #
  print >> log, '*' * 79
  message = result_message(cc12 = cc12, cc13 = cc13, cc23 = cc23)
  print >>log, message
  print >> log, '*' * 79
  print >> log, 'File %s was written.' % polder_file_name
  print >> log, "Finished."
  return True

# =============================================================================
# GUI-specific class for running command
from libtbx import runtime_utils
class launcher (runtime_utils.target_with_save_result) :
  def run (self) :
    import os
    from wxGUI2 import utils
    utils.safe_makedirs(self.output_dir)
    os.chdir(self.output_dir)
    result = cmd_run(args=self.args, validated=True, out=sys.stdout)
    return result

# =============================================================================

if(__name__ == "__main__"):
  t0 = time.time()
  cmd_run(args = sys.argv[1:])
  print "Time:", round(time.time()-t0, 2)
