from dbiface import *

parser = argparse.ArgumentParser(description='Get the idents for a platform/image')
parser.add_argument('platform', metavar='P', type=str, action='store',
                   help='The platform to target')
parser.add_argument('configuration', type=str, action='store',
                   help='The platform configuration')
parser.add_argument('image', type=str, action='store',
                   help='The name of the image')
args = parser.parse_args()

plat = load_platform(args.platform, args.configuration
img = plat.load_image(args.image)
print plat.id, img.id
