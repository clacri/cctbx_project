from __future__ import division
def print_sweep(list_of_images):

    from dxtbx.imageset import ImageSetFactory
    sweeps = ImageSetFactory.new(list_of_images)

    for s in sweeps:
        print s.get_detector()
        print s.get_beam()
        print s.get_goniometer()
        print s.get_scan()

if __name__ == '__main__':
    import sys

    if len(sys.argv) == 2:
        print_sweep(sys.argv[1])
    else:
        print_sweep(sys.argv[1:])
