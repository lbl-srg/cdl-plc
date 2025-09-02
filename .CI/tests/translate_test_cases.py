import sys
sys.path.append('../../')
import argparse
import cdl_plc

cxf_json_path = 'cxf/ModelicaTestCases/'

parser = argparse.ArgumentParser()
parser.add_argument(
    '--output',
    type=str,
    default='./',
    help='Folder where translated files will be saved'
)
args = parser.parse_args()
output_folder = args.output

test_cases = [
    cxf_json_path + 'SingleBlocks/Reals/' + 'Add',
    cxf_json_path + 'SingleBlocks/Reals/' + 'MultiplyByParameter_1',
    cxf_json_path + 'SingleBlocks/Reals/' + 'MultiplyByParameter_2',
    cxf_json_path + 'SingleBlocks/Reals/' + 'PID',

    cxf_json_path + 'CompositeBlocks/' + "CustomPWithLimiter",
    cxf_json_path + 'CompositeBlocks/' + "Custom01",
    cxf_json_path + 'CompositeBlocks/' + "Custom02",
    cxf_json_path + 'CompositeBlocks/' + "Custom03",
]

for test_case in test_cases:
    cxf_json = test_case + ".jsonld"
    cdl_plc.Cdl2Plc(
        cxf_json,
        output_folder=output_folder,
        debug=True,
    ).translate()
