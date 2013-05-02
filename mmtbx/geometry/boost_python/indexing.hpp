#ifndef MMTBX_GEOMETRY_INDEXING_PYTHON_H
#define MMTBX_GEOMETRY_INDEXING_PYTHON_H

#include <string>

#include <boost/python/class.hpp>
#include <boost/python/with_custodian_and_ward.hpp>

#include <boost_adaptbx/boost_range_python.hpp>

#include <mmtbx/geometry/indexing.hpp>

namespace mmtbx
{

namespace geometry
{

namespace indexing
{

namespace python
{

template< typename Indexer >
struct indexer_specific_exports;

template< typename Object >
struct indexer_specific_exports< Linear< Object > >
{
  typedef Linear< Object > indexer_type;
  typedef boost::python::class_< indexer_type > python_class_type;

  static void process(python_class_type& myclass)
  {
    using namespace boost::python;
    myclass.def( init<>() )
      ;
  }
};

template< typename Object, typename Discrete >
struct indexer_specific_exports< Hash< Object, Discrete > >
{
  typedef Hash< Object, Discrete > indexer_type;
  typedef boost::python::class_< indexer_type > python_class_type;

  static void process(python_class_type& myclass)
  {
    using namespace boost::python;
    typedef typename indexer_type::voxelizer_type voxelizer_type;
    myclass.def( init< const voxelizer_type& >( arg( "voxelizer" ) ) )
      .def( "cubes", &indexer_type::cubes )
      ;
  }
};

struct indexer_exports
{
  template< typename Export >
  void operator()(boost::mpl::identity< Export > myexport) const
  {
    typedef typename Export::first indexer_type;
    typedef typename Export::second name_type;

    using namespace boost::python;
    std::string prefix = std::string( boost::mpl::c_str< name_type >::value );

    boost_adaptbx::python::generic_range_wrapper<
      typename indexer_type::range_type
      >::wrap( ( prefix + "_close_objects_range" ).c_str() );

    boost::python::class_< indexer_type > myindexer( prefix.c_str(), no_init );
    myindexer.def( "add", &indexer_type::add, arg( "object" ) )
      .def(
        "close_to",
        &indexer_type::close_to,
        with_custodian_and_ward_postcall< 0, 1 >(),
        arg( "object" )
        )
      .def( "__len__", &indexer_type::size )
      ;
    indexer_specific_exports< indexer_type >::process( myindexer );

  }
};

} // namespace python
} // namespace indexing
} // namespace geometry
} // namespace mmtbx

#endif // MMTBX_GEOMETRY_INDEXING_PYTHON_H
