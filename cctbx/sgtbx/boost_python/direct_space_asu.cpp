#include <cctbx/boost_python/flex_fwd.h>

#include <boost/python/class.hpp>
#include <boost/python/args.hpp>
#include <boost/python/return_value_policy.hpp>
#include <boost/python/copy_const_reference.hpp>
#include <boost/python/return_internal_reference.hpp>
#include <boost/python/return_by_value.hpp>
#include <boost/python/overloads.hpp>
#include <scitbx/boost_python/container_conversions.h>
#include <scitbx/array_family/boost_python/flex_wrapper.h>
#include <cctbx/sgtbx/direct_space_asu.h>

namespace cctbx { namespace sgtbx { namespace direct_space_asu {

namespace {

  struct float_cut_plane_wrappers
  {
    typedef float_cut_plane<> w_t;

    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(
      is_inside_overloads, is_inside, 1, 2)

    static void
    wrap()
    {
      using namespace boost::python;
      typedef boost::python::arg arg_; // gcc 2.96 workaround
      typedef return_value_policy<return_by_value> rbv;
      typedef default_call_policies dcp;
      class_<w_t>("direct_space_asu_float_cut_plane", no_init)
        .def(init<fractional<double> const&, double>((arg_("n"), arg_("c"))))
        .add_property("n",
          make_getter(&w_t::n, rbv()),
          make_setter(&w_t::n, dcp()))
        .def_readwrite("c", &w_t::c)
        .def("evaluate", &w_t::evaluate, (arg_("point")))
        .def("is_inside", &w_t::is_inside, is_inside_overloads(
          (arg_("point"), arg_("epsilon"))))
        .def("get_point_in_plane", &w_t::get_point_in_plane)
        .def("add_buffer", &w_t::add_buffer,
          (arg_("unit_cell"), arg_("thickness")))
      ;
    }
  };

  struct float_asu_wrappers
  {
    typedef float_asu<> w_t;

    BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(
      volume_vertices_overloads, volume_vertices, 0, 2)

    static void
    wrap()
    {
      using namespace boost::python;
      typedef boost::python::arg arg_; // gcc 2.96 workaround
      typedef return_value_policy<copy_const_reference> ccr;
      typedef return_internal_reference<> rir;
      class_<w_t>("direct_space_asu_float_asu", no_init)
        .def(init<uctbx::unit_cell const&,
                  w_t::facets_t const&,
                  optional<double const&> >(
          (arg_("unit_cell"), arg_("facets"), arg_("is_inside_epsilon"))))
        .def("unit_cell", &w_t::unit_cell, rir())
        .def("facets", &w_t::facets, ccr())
        .def("is_inside", &w_t::is_inside, (arg_("point")))
        .def("_add_buffer", &w_t::add_buffer)
        .def("volume_vertices", &w_t::volume_vertices,
          volume_vertices_overloads((arg_("cartesian"), arg_("epsilon"))))
        .def("box_min", &w_t::box_min, ccr())
        .def("box_max", &w_t::box_max, ccr())
      ;
      {
        using namespace scitbx::boost_python::container_conversions;
        tuple_mapping<w_t::facets_t, fixed_capacity_policy>();
      }
    }
  };

  struct asu_mapping_wrappers
  {
    typedef asu_mapping<> w_t;

    static void
    wrap()
    {
      using namespace boost::python;
      typedef return_value_policy<copy_const_reference> ccr;
      class_<w_t>("direct_space_asu_asu_mapping", no_init)
        .def("i_sym_op", &w_t::i_sym_op)
        .def("unit_shifts", &w_t::unit_shifts, ccr())
        .def("mapped_site", &w_t::mapped_site, ccr())
      ;
    }
  };

  struct asu_mappings_wrappers
  {
    typedef asu_mappings<> w_t;

    static void
    wrap()
    {
      using namespace boost::python;
      typedef boost::python::arg arg_; // gcc 2.96 workaround
      typedef return_value_policy<copy_const_reference> ccr;
      typedef return_internal_reference<> rir;
      class_<w_t>("direct_space_asu_asu_mappings", no_init)
        .def(init<space_group const&,
                  float_asu<> const&,
                  double const&,
                  optional<double const&> >(
          (arg_("space_group"),
           arg_("asu"),
           arg_("buffer_thickness"),
           arg_("sym_equiv_epsilon"))))
        .def("reserve", &w_t::reserve, (arg_("n_sites_final")))
        .def("space_group", &w_t::space_group, rir())
        .def("asu", &w_t::asu, rir())
        .def("unit_cell", &w_t::unit_cell, rir())
        .def("buffer_thickness", &w_t::buffer_thickness)
        .def("asu_buffer", &w_t::asu_buffer, rir())
        .def("sym_equiv_epsilon", &w_t::sym_equiv_epsilon)
        .def("buffer_covering_sphere", &w_t::buffer_covering_sphere, rir())
        .def("process", &w_t::process, (arg_("original_site")))
        .def("mappings", &w_t::mappings, ccr())
      ;
      {
        using namespace scitbx::boost_python::container_conversions;
        tuple_mapping<
          w_t::array_of_mappings_for_one_site,
          variable_capacity_policy>();
      }
      {
        scitbx::af::boost_python::flex_wrapper<
          w_t::array_of_mappings_for_one_site>::plain(
            "direct_space_asu_array_of_array_of_mappings_for_one_site");
      }
    }
  };

}} // namespace direct_space_asu::<anoymous>

namespace boost_python {

  void wrap_direct_space_asu()
  {
    direct_space_asu::float_cut_plane_wrappers::wrap();
    direct_space_asu::float_asu_wrappers::wrap();
    direct_space_asu::asu_mapping_wrappers::wrap();
    direct_space_asu::asu_mappings_wrappers::wrap();
  }

}}} // namespace cctbx::sgtbx::boost_python
