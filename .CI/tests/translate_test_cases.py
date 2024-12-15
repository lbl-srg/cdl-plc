import cdl_plc

cxf_json_path = '../../cxf/ModelicaTestCases/'

test_cases = [
    cxf_json_path + 'SingleBlocks/Reals/' + 'Add',
    cxf_json_path + 'SingleBlocks/Reals/' + 'MultiplyByParameter',

    cxf_json_path + 'CompositeBlocks/' + "customPWithLimiter",
    cxf_json_path + 'CompositeBlocks/' + "Custom01",
    cxf_json_path + 'CompositeBlocks/' + "Custom02",
    cxf_json_path + 'CompositeBlocks/' + "Custom03",
]

for test_case in test_cases:
    cxf_json = test_case + ".jsonld"
    cdl_plc.Cdl2Plc(cxf_json, debug=True).translate()
