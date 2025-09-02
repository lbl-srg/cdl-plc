import json
import jinja2
import xml.dom.minidom
import shutil
import ast
import numbers
import os
from pathlib import Path
import cdl_composite_blocks
import iec_standard_function_names

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
print(dname)
os.chdir(dname)


def evaluate_safe_expression(expr):

    print('evaluating:', expr)
    print('type:', type(expr))

    try:
        # If expr is already a number, return it directly
        if isinstance(expr, (int, float)):
            print('Input is int or float. Already a valid number.')
            return expr

        # Ensure expr is a string before parsing
        if not isinstance(expr, str):
            print('Input is not a string. Invalid input.')
            return None

        # Parse the expression
        node = ast.parse(expr, mode='eval')

        # Special case expression is just a single number
        if isinstance(node.body, ast.Constant):
            print('input is just a single number as string')
            return eval(expr)

        # Allow only safe node types
        allowed_types = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.Constant,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Mod,
            ast.Pow,
            ast.FloorDiv,
            ast.USub,  # Allows negative numbers
        )

        if all(isinstance(n, allowed_types) for n in ast.walk(node)):
            print('Safe to evaluate. Evaluate string.')
            result = eval(expr)
            print('result', result)
            return result
        else:
            print('Unsafe operation detected.')
            return None

    except (SyntaxError, ValueError, TypeError, NameError):
        print('Error. Invalid expression.')

        return None


def return_iec_data_type(input):
    """
    Returns an IEC data type string from...
    """

    if isinstance(input, float):
        par_value_type = "REAL"
        parameter_value_local = input
    elif isinstance(input, int) and not isinstance(input, bool):
        # Re-format
        parameter_value_local = "{:.1f}".format(input)
        par_value_type = "REAL"
    elif isinstance(input, bool):
        par_value_type = "BOOL"
        parameter_value_local = input
    else:
        print('Case not covered')
        par_value_type = None
        parameter_value_local = None

    return par_value_type, parameter_value_local


class Cdl2Plc:

    """
    Note: The order of inputs of function blocks (in case they have multiple inputs)
    depends on the order in the function block XML template/snipped.
    The JSONLD might have another order of inputs.
    If these two orders do not match, parameter inputs are not rendered correctly (in the same order).
    However, they are still connected correctly.
    """

    dict_assign_cdl_to_iec_standard_lib = {
        "Reals_Greater": {
            'name_iec': "GT",
            'mapping_ios': {
                'u1': 'IN1',
                'u2': 'IN2',
                'y': 'OUT',
            },
        },
        "Logical_And": {
            'name_iec': "AND",
            'mapping_ios': {
                'u1': 'IN1',
                'u2': 'IN2',
                'y': 'OUT',
            },
        },
        "Reals_Add": {
            'name_iec': "ADD",
            'mapping_ios': {
                'u1': 'IN1',
                'u2': 'IN2',
                'y': 'OUT',
            },
        },
        "Reals_Subtract": {
            'name_iec': "SUB",
            'mapping_ios': {
                'u1': 'IN1',
                'u2': 'IN2',
                'y': 'OUT',
            },
        },
        "Reals_Multiply": {
            'name_iec': "MUL",
            'mapping_ios': {
                'u1': 'IN1',
                'u2': 'IN2',
                'y': 'OUT',
            },
        },
        "Logical_Not": {
            'name_iec': "NOT",
            'mapping_ios': {
                'u': 'IN',
                'y': 'OUT',
            },
        },
        "Conversions_BooleanToInteger": {
            'name_iec': "BOOL_TO_INT",
            'mapping_ios': {
                'u': 'IN',
                'y': 'OUT',
            },
        },
        "Conversions_BooleanToReal": {
            'name_iec': "BOOL_TO_REAL",
            'mapping_ios': {
                'u': 'IN',
                'y': 'OUT',
            },
        },
    }

    dict_CDL_to_OSCAT = {
        "CDL_Reals_PID": "CTRL_PID"
    }

    dict_map_blocks_to_files = {
        "Reals_Add": ["Reals_Add"],
        "Reals_Min": ["Reals_Min"],
        "Reals_MultiplyByParameter": ["Reals_MultiplyByParameter"],
        "Reals_Hysteresis": ["Reals_Hysteresis"],
        "Reals_PID": [
            "Reals_PID",
            'Reals_MultiplyByParameter',
            'Reals_Limiter',
            'INTEGRATE',
            'T_PLC_MS',
        ],
        "Reals_Sources_Constant": ["Reals_Sources_Constant"],
        "Reals_Line": ["Reals_Line"],
        "Reals_MovingAverage": ["Reals_MovingAverage"],
        "Reals_Switch": ["Reals_Switch"],
        "Reals_Limiter": ["Reals_Limiter"],
    }

    available_node_types = {
        "parameter_definition": 1,  # can be a parameter assignment within a CDL block
        "parameter_assignment": 2,  # Is a node where a value is assigned to a parameter
        "connection": 3,
        "fb_instance": 4,
        "fb_instance_iec": 5,
        "output_real": 6,
        "output_bool": 7,
        "input_real": 8,
        "input_bool": 9,
        "program": 10,
        "input_int": 11,
        "output_int": 12,
        "user_defined_composite_block": 13,
        "block_composite": 14,
    }

    def __init__(
            self,
            cxf_filename,
            output_folder=None,
            debug=False,
    ):

        self.io_height = 26

        self.cxf_file = cxf_filename
        self.output_folder = Path(output_folder)

        # properties
        self._multi_input_blocks = None
        self._cxf_graph = None
        self._cxf_instances = None

        self.cxf_blocks = None
        self.cxf_outputs = None

        self._xml_local_ids = None

        self.output_text = None
        self._program_name = None

        # self._global_xy_shift = None
        self._x_shift = None
        self._y_shift = None
        self.user_defined_composite_block_xml_snippets = []

        self.debug = debug
        self.jsonld_directory = Path(cxf_filename).parent
        self.jsonld = self.load_jsonld(Path(cxf_filename))
        self._cxf_connection_structure = self.create_cxf_connection_structure()
        self._dict_connections = self.create_dict_connections()
        self._program_parameters = self.collect_xml_parameters()
        self.program_inputs, self.program_outputs, self.program_fb_instances, self.program_fb_instances_iec, self.program_user_defined_composite_blocks, self.program_fb_instances_block_composite = self.create_dicts_for_jinja()
        self.dict_xml_snippets_of_cdl_block_classes = {
            "scalar_inputs": set(),
            "array_inputs": set(),
        }
        self.read_and_collect_cdl_block_snippets(self.program_fb_instances)
        self.read_and_collect_cdl_block_snippets(self.program_fb_instances_block_composite)
        self.add_absolute_x_y_coordinates_of_connectors()
        # self.add_source_block_connector_coordinates()

    def add_absolute_x_y_coordinates_of_connectors(self):
        """
        Adds absolute x and y coordinates for generation of connections in XML
        """

        def get_positions_from_block(input_block):
            x_absolute_function_block_instance = input_block['x_absolute']
            y_absolute_function_block_instance = input_block['y_absolute']
            width_absolute_function_block_instance = input_block['width']

            return x_absolute_function_block_instance, y_absolute_function_block_instance, width_absolute_function_block_instance

        # step 1: get absolute x-y-coordinates of connection target
        # write in dict
        # loop over regular function block instances
        def update_dict_with_target_connector_coordinates(input_dict):
            for function_block_instance in input_dict:

                x, y, width = get_positions_from_block(input_dict[function_block_instance])

                dict_inputs = input_dict[function_block_instance]['inputs']
                dict_outputs = input_dict[function_block_instance]['outputs']

                print('dict with inputs', dict_inputs)
                print('dict with outputs', dict_outputs)

                # loop over function block instance inputs
                for count_input, (target_connector_name, parameters) in enumerate(dict_inputs.items()):

                    # get absolute input connector x-y-coordinates
                    print('count input', count_input)
                    print('input name', target_connector_name)
                    print('input parameters', parameters)
                    parameters['x_absolute'] = x
                    parameters['y_absolute'] = y + self.calc_relative_y_position_of_io(count_input)
                    parameters['x_relative'] = 0
                    parameters['y_relative'] = self.calc_relative_y_position_of_io(count_input)

                # loop over function block instance outputs
                for count_output, (output_name, parameters) in enumerate(dict_outputs.items()):
                    print('count output', count_output)
                    print('output name', output_name)
                    print('output parameters', parameters)
                    # NOTE: this only covers cases where output (are a list) have only one element
                    # probably has to be adjusted in case with one output to multiple inputs
                    parameters[0]['x_absolute'] = x + width
                    parameters[0]['y_absolute'] = y + self.calc_relative_y_position_of_io(count_output)
                    parameters[0]['x_relative'] = width
                    parameters[0]['y_relative'] = self.calc_relative_y_position_of_io(count_output)

        update_dict_with_target_connector_coordinates(self.program_fb_instances)
        update_dict_with_target_connector_coordinates(self.program_fb_instances_block_composite)
        update_dict_with_target_connector_coordinates(self.program_fb_instances_iec)
        update_dict_with_target_connector_coordinates(self.program_user_defined_composite_blocks)

        # loop over input blocks
        for input_block, parameters in self.program_inputs.items():

            print('input block', input_block)
            print('input block parameters', parameters)

            x, y, width = get_positions_from_block(self.program_inputs[input_block])

            parameters['connector_x_absolute'] = x + width
            parameters['connector_y_absolute'] = y + int(self.io_height / 2)

        # loop over output blocks
        for output_block, parameters in self.program_outputs.items():

            print('output block', output_block)
            print('output block parameters', parameters)

            x, y, width = get_positions_from_block(self.program_outputs[output_block])

            parameters['connector_x_absolute'] = x
            parameters['connector_y_absolute'] = y + int(self.io_height / 2)

        # step 2: get x-y-coordinates of connection source
        print('Get x-y-coordinates of source connectors')

        def add_connection_string(input_dict):
            """
            Adds connection strings to connector inputs based on an input dict of function blocks.
            Function blocks can be regular CDL blocks, IEC standard blocks, or user-defined composite blocks.
            """

            print('Adding connection strings for function block input connectors based on dict:', input_dict)

            # loop over function block instances
            for function_block_instance in input_dict:

                print('Function block instance:', function_block_instance)

                # dict_inputs = self.program_fb_instances[function_block_instance]['inputs']

                dict_with_inputs = input_dict[function_block_instance]['inputs']

                if self.debug:
                    print('Dict with input connectors:', dict_with_inputs)

                # loop over inputs of each function block instance
                for target_connector_name, target_connector_attributes in dict_with_inputs.items():

                    print('Target connector name:', target_connector_name)
                    print('Target connector attributes:', target_connector_attributes)

                    # get absolute connector source x-y-coordinates
                    source_block_connector = target_connector_attributes['source_block_connector']
                    print('Source connector:', source_block_connector)

                    # check if source block instance is a function block or a program input
                    if source_block_connector == '':

                        if 'source_block_instance' in target_connector_attributes.keys():
                            print('Source connector is a program input.')
                            source_is_program_input = True
                            source_is_program_parameter = False
                            source_is_function_block_instance = False
                        else:
                            print('Source connector is a program parameter.')
                            source_is_program_input = False
                            source_is_program_parameter = True
                            source_is_function_block_instance = False

                    else:
                        print('Source connector is part of a function block instance.')
                        source_is_program_input = False
                        source_is_program_parameter = False
                        source_is_function_block_instance = True

                    # get x-y-coordinates of target connector
                    x_target_absolute = target_connector_attributes['x_absolute']
                    y_target_absolute = target_connector_attributes['y_absolute']

                    # look up source connector x-y-coordinates
                    # Case: input connector connected to program inputs
                    if source_is_program_input:

                        print('Show all program inputs', self.program_inputs)

                        source_block_instance = target_connector_attributes['source_block_instance']

                        x_source_connector_absolute = self.program_inputs[source_block_instance]['x_absolute']
                        y_source_connector_absolute = self.program_inputs[source_block_instance]['y_absolute']

                        print('x-y-coordinates of source connector', x_source_connector_absolute, y_source_connector_absolute)

                        input_dict[function_block_instance]['inputs'][target_connector_name]['x_absolute_source_connector'] = x_source_connector_absolute
                        input_dict[function_block_instance]['inputs'][target_connector_name]['y_absolute_source_connector'] = y_source_connector_absolute

                    # Case: input connector connected to program parameter
                    elif source_is_program_parameter:

                        print('show all program parameters', self._program_parameters)

                        # find source parameter from source ID
                        source_id = target_connector_attributes['id']
                        source_parameter = self.find_parameter_from_id(source_id)

                        print('source parameter', source_parameter)

                        # Get x-y-coordinates of source block connector
                        x_source_connector_absolute = x_target_absolute - 20
                        y_source_connector_absolute = y_target_absolute

                        # update parameter block x-y-coordinates
                        self._program_parameters[source_parameter]['x_absolute_connector'] = x_source_connector_absolute
                        self._program_parameters[source_parameter]['y_absolute_connector'] = y_source_connector_absolute
                        self._program_parameters[source_parameter]['x_absolute'] = x_target_absolute - 20 - self._program_parameters[source_parameter]['width']
                        self._program_parameters[source_parameter]['y_absolute'] = y_target_absolute - int(self._program_parameters[source_parameter]['height'] / 2)

                        print('show all program parameters with updated x-y-coordinates', self._program_parameters)

                        print('input attributes', target_connector_attributes)

                        input_dict[function_block_instance]['inputs'][target_connector_name]['x_absolute_source_connector'] = x_target_absolute - 20
                        input_dict[function_block_instance]['inputs'][target_connector_name]['y_absolute_source_connector'] = y_target_absolute

                    # Case: input connector connected to program function block instance
                    if source_is_function_block_instance:

                        if self.debug:
                            print('Input connector is connected to output of function block instance.')

                        source_block_instance = target_connector_attributes['source_block_instance']

                        if self.debug:
                            print('Source instance:', source_block_instance)

                        if source_block_instance in self.program_fb_instances:

                            if self.debug:
                                print('Source instance is a regular function block instance')

                            source_block_instance_outputs = self.program_fb_instances[source_block_instance]['outputs'][source_block_connector][0]

                        elif source_block_instance in self.program_fb_instances_iec:

                            if self.debug:
                                print('Source instance is an IEC standard function block instance')

                            source_block_instance_outputs = self.program_fb_instances_iec[source_block_instance]['outputs'][source_block_connector][0]

                        elif source_block_instance in self.program_user_defined_composite_blocks:

                            if self.debug:
                                print('Source instance is a user defined function block instance')

                            source_block_instance_outputs = self.program_user_defined_composite_blocks[source_block_instance]['outputs'][source_block_connector][0]

                        elif source_block_instance in self.program_fb_instances_block_composite:

                            if self.debug:
                                print('Source instance is a CDL composite elementary block.')

                            source_block_instance_outputs = self.program_fb_instances_block_composite[source_block_instance]['outputs'][source_block_connector][0]

                        else:

                            print('Source instance is not assigned.')

                        if self.debug:
                            print('Outputs of the function block instance:', source_block_instance_outputs)

                        # Get x-y-coordinates of source block connector
                        x_source_connector_absolute = source_block_instance_outputs['x_absolute']
                        y_source_connector_absolute = source_block_instance_outputs['y_absolute']

                        input_dict[function_block_instance]['inputs'][target_connector_name]['x_absolute_source_connector'] = x_source_connector_absolute
                        input_dict[function_block_instance]['inputs'][target_connector_name]['y_absolute_source_connector'] = y_source_connector_absolute

                    # Generate connector string
                    connector_string = self.generate_connector_string(
                        x_target_absolute,
                        y_target_absolute,
                        x_source_connector_absolute,
                        y_source_connector_absolute,
                    )

                    print('Connector string', connector_string)

                    # Add connector string to dicts
                    # if source_is_function_block_instance:
                    input_dict[function_block_instance]['inputs'][target_connector_name][
                        'connector_string'] = connector_string

        def add_connection_string_to_outputs(input_dict):
            """
            Adds a connection string to program outputs
            """

            print('Adding connection strings for program outputs based on dict:', input_dict)

            # loop over
            for output_block, output_block_attributes in input_dict.items():

                # get target connector x-y-coordinates
                x_target_connector_absolute = output_block_attributes['connector_x_absolute']
                y_target_connector_absolute = output_block_attributes['connector_y_absolute']

                # get source connector x-y-attributes
                # get source information
                source_block_instance = output_block_attributes['input_connector']['source_block_instance']
                source_block_connector = output_block_attributes['input_connector']['source_block_connector']

                print('Source block instance:', source_block_instance)
                print('Source block connector:', source_block_connector)

                # Check the type of the source block instance
                # Depending on the source block type, a different dict is selected
                if source_block_instance in self.program_fb_instances:
                    print('Source block instance is a regular CDL block:', self.program_fb_instances)
                    function_block_dict = self.program_fb_instances
                elif source_block_instance in self.program_fb_instances_block_composite:
                    print('Source block instance is a composite CDL block:', self.program_fb_instances_block_composite)
                    function_block_dict = self.program_fb_instances_block_composite
                elif source_block_instance in self.program_fb_instances_iec:
                    print('Source block instance is a CDL block with direct assignment to an IEC block:', self.program_fb_instances_block_composite)
                    function_block_dict = self.program_fb_instances_iec
                else:
                    print(f'{source_block_instance} can not be assigned to a type of blocks.')

                x_source_connector_absolute = function_block_dict[source_block_instance]['outputs'][source_block_connector][0]['x_absolute']
                y_source_connector_absolute = function_block_dict[source_block_instance]['outputs'][source_block_connector][0]['y_absolute']

                print('Source block x_absolute:', x_source_connector_absolute)
                print('Source block y_absolute:', y_source_connector_absolute)

                # Generate connector string
                connector_string = self.generate_connector_string(
                    x_target_connector_absolute,
                    y_target_connector_absolute,
                    x_source_connector_absolute,
                    y_source_connector_absolute
                )

                print('Connector string', connector_string)

                # Add connector string to dicts
                # if source_is_function_block_instance:
                input_dict[output_block]['input_connector']['connector_string'] = connector_string

        add_connection_string(self.program_fb_instances)
        add_connection_string(self.program_fb_instances_block_composite)
        add_connection_string(self.program_fb_instances_iec)
        add_connection_string(self.program_user_defined_composite_blocks)
        add_connection_string_to_outputs(self.program_outputs)

    # @staticmethod
    def get_instance_name_from_node(self, node, debug=True):
        """
        Parses the block instance string.
        Returns parts after the program name.
        """

        node_id_after_program_name = node["@id"].split(f".{self.program_name}.")
        stripped_node_id_string = node_id_after_program_name[-1].split(".")

        if debug:
            print('Stripped node ID string: ', stripped_node_id_string)

        return stripped_node_id_string

    # @staticmethod
    def find_parameter_from_id(self, id):
        for parameter, attributes in self._program_parameters.items():
            if attributes['localId'] == id:
                return parameter

    @staticmethod
    def generate_connector_string(
            x_target_absolute,
            y_target_absolute,
            x_source_connector_absolute,
            y_source_connector_absolute
    ):
        return f'<position x="{x_target_absolute}" y="{y_target_absolute}"/><position x="{int((x_target_absolute + x_source_connector_absolute) / 2)}" y="{y_target_absolute}"/><position x="{int((x_target_absolute + x_source_connector_absolute) / 2)}" y="{y_source_connector_absolute}"/><position x="{x_source_connector_absolute}" y="{y_source_connector_absolute}"/>'

    @staticmethod
    def calc_relative_y_position_of_io(count_input):
        return 10 + (count_input + 1) * 20

    @staticmethod
    def calc_block_width(name_string):
        if isinstance(name_string, str):
            return len(name_string) * 8 + 10
        elif isinstance(name_string, list):
            max_length = max([len(x) for x in name_string])
            return max_length * 8 + 10

    @staticmethod
    def calc_block_height(number_ios):
        # return 12 + number_ios * 14
        return 20 + number_ios * 20

    @staticmethod
    def get_class_name_from_user_defined_composite_block(node, debug=True):
        return node["@type"].split("#")[1].split('.')[-1]

    @staticmethod
    def get_class_name_from_cdl_block(node, debug=True):
        stripped = '_'.join(node["@type"].split("#")[-1].split(".")[4:])
        if debug:
            print('stripped: ', stripped)
        return stripped

    @property
    def xml_local_ids(self):
        if self._xml_local_ids is None:
            self.create_xml_local_ids()
        return self._xml_local_ids

    def get_cdl_block_class_name(self, instance_name, debug=True):
        """
        get name of CDL block instance and name of associated CDL block classes
        """

        #
        cxf_instances = self.cxf_instances

        if debug:
            print('cxf_instances', cxf_instances)

        # get the name of the CDL block class
        cdl_block_class_name = cxf_instances[instance_name]

        # replace
        cdl_block_class_name = cdl_block_class_name.replace(".", "_")

        return cdl_block_class_name

    # @property
    def create_xml_local_ids(self, debug=False):
        """
        create dict with local Ids
        """

        self._xml_local_ids = {}
        local_id = 1

        # loop over JSON-LD
        for i, node in enumerate(self.cxf_graph):
            if debug:
                print("i-iterator:", i)
                print("node:", node)
            node_type = self.check_jsonld_graph_node_type(node, debug=debug)
            if debug:
                print("node_type:", node_type)
            if node_type in [
                self.available_node_types["fb_instance"],
                self.available_node_types["fb_instance_iec"],
                self.available_node_types["input_real"],
                self.available_node_types["input_bool"],
                self.available_node_types["input_int"],
                self.available_node_types["output_real"],
                self.available_node_types["output_bool"],
                self.available_node_types["output_int"],
                self.available_node_types["user_defined_composite_block"],
                self.available_node_types["block_composite"],
            ]:
                node_label = node["S231P:label"]
                self._xml_local_ids[node_label] = local_id

                local_id += 1

        if debug:
            print("Local IDs in XML:", self._xml_local_ids)

        # loop over parameters separetly
        # parameters can not be taken from the JSON-LD directly
        list_parameters = [
            self.check_parameter_string(x['S231P:value']) for x in
            self.select_jsonld_graph_nodes_by_types([self.available_node_types["parameter_definition"]])
        ]
        if debug:
            print("list_parameters", list_parameters)

        for par in list_parameters:
            self.xml_local_ids[par] = local_id
            local_id += 1

        if debug:
            print("xml_local_ids", self.xml_local_ids)

        # return self.xml_local_ids

    def get_graph_info(self, node, shift=True, debug=False):
        """
        Retrieves graphical information from a JSON node and calculates the position
        and size of a graphical element.

        Parameters:
        node (dict): The JSON node containing graphical information.
        shift (tuple, optional): A tuple representing the shift in x and y coordinates.
            If provided, the position of the graphical element will be shifted accordingly.
            Defaults to False.
        debug (bool, optional): If True, debug information will be printed.
            Defaults to False.

        Returns:
        tuple: A tuple containing the x and y coordinates, width, and height of the graphical element.
        """

        graph_info = ast.literal_eval(node["S231P:graphics"])["Placement"]["transformation"]["extent"]
        if debug:
            print("graphical info from jsonLD", graph_info)

        x = graph_info[0]["x"]
        y = graph_info[0]["y"]

        width = graph_info[1]["x"] - x
        height = graph_info[1]["y"] - y
        if shift:
            scale_factor_x = 4
            scale_factor_y = 2
            x = (x + self.x_shift) * scale_factor_x
            y = (y + height - self.y_shift) * scale_factor_y
        if debug:
            print("x/y/width/height", x, y, width, height)

        return x, y, width, height

    @staticmethod
    def check_parameter_string(value):
        """
        Checks if the given value is an integer and constructs a parameter string accordingly.

        If the value is an integer, it constructs a parameter string with the format "r{value}",
        where {value} is the integer value provided. Otherwise, it returns the value as is.

        Parameters:
        value: The value to be checked and converted to a parameter string.

        Returns:
        str: A parameter string constructed based on the input value.
        """

        value_type = evaluate_safe_expression(value)

        if isinstance(value_type, numbers.Number):
            par_str = "_{}".format(str(value_type).replace('.', '_'))
        else:
            par_str = value
        return par_str

    def parse_id_key(self, check_node):
        """
        Parses an ID key from a node and splits it into instance and link parts.

        This function takes a node with an ID key and splits the ID key into
        instance and link parts. It returns a dictionary containing these parts.

        Parameters:
        check_node (dict): The node to parse the ID key from.
        debug (bool, optional): If True, debug information will be printed.
            Defaults to False.

        Returns:
        dict: A dictionary containing the instance and link parts of the ID key.
        """

        if self.debug:
            print("check_node:", check_node)

        output = self.get_instance_name_from_node(check_node)
        if self.debug:
            print("output", output)
        if len(output) == 2:
            instance, link = output
        else:
            instance = output[0]
            link = ""
        if self.debug:
            print("instance:", instance)
            print("source_block_connector:", link)
        output = {"instance": instance, "source_block_connector": link}
        if self.debug:
            print("output:", output)

        return output

    def extract_id_instance(
            self,
            input_structure,
    ):
        """
        Extracts instance values from a structure containing IDs.

        This function takes a structure containing IDs, which can be either a list
        or a dictionary, and extracts the instance values associated with those IDs.
        It returns a list of instance values.

        Parameters:
        input_structure (list or dict): The structure containing IDs.
        debug (bool, optional): If True, debug information will be printed.
            Defaults to False.

        Returns:
        list: A list containing instance values extracted from the input structure.
        """

        if self.debug:
            print("input_structure", input_structure)
        if isinstance(input_structure, list):
            if self.debug: print("input_structure is a list")
            output = [self.parse_id_key(x)["instance"] for x in input_structure]
        elif isinstance(input_structure, dict):
            if self.debug:
                print("input_structure is a dict")
            output = [
                self.parse_id_key(input_structure)["instance"]
            ]
        return output

    # @property
    # def load_xml_parameters(self):
    #     if self._program_parameters is None:
    #         self.collect_xml_parameters()
    #     return self._program_parameters

    def collect_xml_parameters(self, debug=True):
        """
        creates a dict with local parameters
        """

        self._program_parameters = {}

        # loop over nodes
        for node in self.cxf_graph:

            # check node type
            node_type = self.check_jsonld_graph_node_type(node)

            # if node is 'parameter_definition'
            if node_type == 1:
                if debug:
                    print("Node with parameter definition:", node)

                def extract_parameter_value(input_node):
                    """
                    Finds the value for a parameter
                    """

                    # Gets the value of the 'value' key
                    node_value_local = input_node['S231P:value']

                    if debug:
                        print("'value' key of the parameter node:", node_value_local)
                        print("Type of the node_value:", type(node_value_local))

                    # Checks the type of the value
                    type_node_value_local = evaluate_safe_expression(node_value_local)

                    print('type_node_value_local', type_node_value_local)

                    # case: parameter is numeric
                    if isinstance(type_node_value_local, numbers.Number):
                        if debug:
                            print('The parameter is numeric')
                        parameter_value_local = type_node_value_local

                        # Get the IEC data type
                        par_value_type, parameter_value_local = return_iec_data_type(parameter_value_local)

                    # case: parameter is a variable
                    # find the corresponding value
                    else:
                        if debug:
                            print('The parameter is a variable / input')

                        # Take nodes with parameters assignments
                        nodes_with_parameter_assignments = self.select_jsonld_graph_nodes_by_types(
                                [2],
                        )

                        if debug:
                            print('Nodes with parameter assignments:', nodes_with_parameter_assignments)

                        # Loop over nodes with parameter assignments
                        for node_with_parameter_assignment in nodes_with_parameter_assignments:

                            if debug:
                                print('Node with parameter assignment:', node_with_parameter_assignment)

                            # It's the correct node if the 'label' value matches the corresponding parameter
                            if node_with_parameter_assignment["S231P:label"] == node_value_local:
                                parameter_value_local = node_with_parameter_assignment["S231P:value"]
                                par_value_type, parameter_value_local = return_iec_data_type(parameter_value_local)

                    if self.debug:
                        print('node_value_local:', node_value_local)
                        print('parameter_value_local:', parameter_value_local)
                        print('par_value_type:', par_value_type)

                    return node_value_local, parameter_value_local, par_value_type

                # extract parameter value
                node_value, parameter_value, parameter_value_type = extract_parameter_value(node)

                instance = self.parse_id_key(node)["instance"]
                link = self.parse_id_key(node)["source_block_connector"]
                if self.debug:
                    print("instance", instance)
                    print("source_block_connector", link)

                # def get_local_id(node_value):
                parameter_string = self.check_parameter_string(node_value)
                local_id = self.xml_local_ids[parameter_string]
                #     return parameter_string, local_id
                #
                # parameter_string, local_id = get_local_id()

                if self.debug:
                    print('parameter_string', parameter_string)

                width = self.calc_block_width(parameter_string)
                height = self.io_height

                self._program_parameters[parameter_string] = {
                    "instance": instance,
                    "source_block_connector": link,
                    "value": parameter_value,
                    "valueType": parameter_value_type,
                    "localId": local_id,
                    "width": width,
                    "height": height,
                }

        return self._program_parameters

    def create_cxf_connection_structure(self, debug=True):
        """
        Creates a structure for connections based on input data.

        This function processes the input data to create a dictionary structure for connections.
        It detects blocks and outputs, initializes dictionaries for connections, and returns
        the constructed structure along with lists of detected blocks and outputs.

        Parameters:
        input (dict): The input data containing information about blocks and connections.
            This is derived from the CXF dict graph program node
        debug (bool, optional): If True, debug information will be printed. Defaults to False.

        Returns:
        tuple: A tuple containing:
            - dict: A dictionary representing the structure for connections.
            - list: A list of detected blocks.
            - list: A list of detected outputs.
        """

        # select nodes of type 'program'
        program_string = "program"
        program_node_type = self.available_node_types[program_string]
        dict_input = self.select_jsonld_graph_nodes_by_types([program_node_type])[0]

        if debug:
            print(f'Input dict with "program" types {program_node_type}', dict_input)

        # instantiate connection structure
        self._cxf_connection_structure = {}

        # detect blocks
        self.cxf_blocks = self.extract_id_instance(
            dict_input["S231P:containsBlock"],
        )

        if self.debug:
            print("Function block instances in the program:", self.cxf_blocks)

        # from_block = node["@id"].split("#")[-1].split(".")[0]

        # loop over function block instances and add to dict
        for block in self.cxf_blocks:

            # # check if instance name is equal to associated class name
            # type_block_instance = self.check_jsonld_graph_node_type(node)

            self._cxf_connection_structure[block] = {"input": {}, "output": {}}

        if self.debug:
            print("dict_connections:", self._cxf_connection_structure)

        # detect outputs
        self.cxf_outputs = self.extract_id_instance(
            dict_input["S231P:hasOutput"],
        )
        if self.debug:
            print("outputs:", self.cxf_outputs)

        for output in self.cxf_outputs:
            self._cxf_connection_structure[output] = {"input": {}}
        if self.debug:
            print("dict_connections:", self._cxf_connection_structure)
            print("cxf_blocks:", self.cxf_blocks)
            print("cxf_outputs:", self.cxf_outputs)

        return self._cxf_connection_structure

    @property
    def x_shift(self):
        if self._x_shift is None:
            self.get_global_xy_shift()
        return self._x_shift

    @property
    def y_shift(self):
        if self._y_shift is None:
            self.get_global_xy_shift()
        return self._y_shift

    # @property
    def get_global_xy_shift(self, debug=False):
        """
        collect information for graphics
        """

        list_x_min = []
        list_y_min = []
        list_y_max = []

        for node in self.cxf_graph:
            if "S231P:graphics" in node.keys():
                x, y, width, height = self.get_graph_info(node, shift=False)
                list_x_min.append(x)
                list_y_min.append(y)
                list_y_max.append(y + height)
        if debug:
            print("list_x_min: ", list_x_min)
            print("list_y_min: ", list_y_min)
            print("list_y_max: ", list_y_max)

        y_diff = max(list_y_max) - min(list_y_min)

        self._x_shift = abs(min(min(list_x_min), 0))
        self._y_shift = max(list_y_max)

        if debug:
            print("x_shift: ", self._x_shift)
            print("y_shift: ", self._y_shift)
            print("y_diff: ", y_diff)

    def select_jsonld_graph_nodes_by_types(
            self,
            node_types=[],
            debug=True,
    ):
        """
        Groups nodes of specific types from a graph.

        This function iterates over nodes in the provided graph and filters out nodes
        based on their type. It creates a list containing nodes that match the specified types.

        Parameters:
        graph (dict): The graph containing nodes to be filtered.
        types (list): A list of node types to be included in the resulting list.

        Returns:
        list: A list containing nodes from the graph that match the specified types.
        """

        # if no node types are selected, take all
        if node_types is []:
            node_types = self.available_node_types

        if debug:
            print('selecting the following node types:', node_types)

        # instantiate empty list
        list_return = []

        print('cxf graph:', self.cxf_graph)

        # iterate over JSONLD graph
        for node in self.cxf_graph:

            if debug:
                print(f"node of selected type(s) {node_types}", node)

            # check node type
            node_type = self.check_jsonld_graph_node_type(node)

            if self.debug:
                print("node_type", node_type)

            if node_type in node_types:
                list_return.append(node)

        return list_return

    # def check_block_instance_type(self, input_name):
    #
    #     # loop over graph nodes
    #     for node in self.cxf_graph:
    #         if "S231P:label" in node.keys():
    #             class_name = self.

    def check_jsonld_graph_node_type(self, node, debug=False):
        """
        This function checks the type of a node of the cxf graph
        """

        if debug:
            print("node:", node)
        keys = list(node.keys())

        if debug:
            print('set keys:', set(keys))

        node_type = None

        # Parameter definition
        # this is a parameter of a block
        if set(keys).issubset({"@id", "S231P:isFinal", "S231P:value"}):

            # get instance name
            instance_name = node["@id"].split("#")[-1].split(".")[-2]

            # get corresponding class name
            class_name = self.get_cdl_block_class_name(instance_name, debug=debug)

            if debug:
                print('instance_name:', instance_name)
                print('class_name:', class_name)

            if class_name in self.multi_input_blocks:
                node_type = self.available_node_types["nin_fb_instance"]
            else:
                node_type = self.available_node_types["parameter_definition"]

        # Parameter assignment
        elif ("@type" in keys) and (node["@type"] == "S231P:Parameter"):

            node_type = self.available_node_types["parameter_assignment"]

        # Connection
        elif keys == ["@id", "S231P:isConnectedTo"]:

            check_is_connected_to_keys = node["S231P:isConnectedTo"]

            id_key_only = None

            # if output connected to multiple inputs (?)
            if isinstance(check_is_connected_to_keys, list):
                # check if "@id" is the only key
                # set_check = set()
                if all([list(x.keys()) == ["@id"] for x in check_is_connected_to_keys]):
                    id_key_only = True

            # if output connected to one input (?)
            elif isinstance(check_is_connected_to_keys, dict):
                if list(node["S231P:isConnectedTo"].keys())[0] == "@id":
                    id_key_only = True
            if id_key_only:
                node_type = self.available_node_types["connection"]

        elif ("@type" in keys) and (node["@type"] == "S231P:RealOutput"):
            node_type = self.available_node_types["output_real"]

        elif ("@type" in keys) and (node["@type"] == "S231P:BooleanOutput"):
            node_type = self.available_node_types["output_bool"]

        elif ("@type" in keys) and (node["@type"] == "S231P:IntegerOutput"):
            node_type = self.available_node_types["output_int"]

        elif ("@type" in keys) and (node["@type"] == "S231P:RealInput"):
            node_type = self.available_node_types["input_real"]

        elif ("@type" in keys) and (node["@type"] == "S231P:BooleanInput"):
            node_type = self.available_node_types["input_bool"]

        elif ("@type" in keys) and (node["@type"] == "S231P:IntegerInput"):
            node_type = self.available_node_types["input_int"]

        # CDL blocks
        elif set(keys).issubset({
            "@id",
            "@type",
            "S231P:accessSpecifier",
            "S231P:graphics",
            "S231P:description",
            "S231P:label",
            "S231P:hasInstance",
        }) and (
                node["@type"].split("#")[0] == "https://data.ashrae.org/S231P"):

            cdl_class_name = self.get_class_name_from_cdl_block(node, debug=debug)

            if debug:
                print("Class name of the CDL block:", cdl_class_name)

            if cdl_class_name in self.dict_assign_cdl_to_iec_standard_lib:
                node_type = self.available_node_types["fb_instance_iec"]
            elif cdl_class_name in cdl_composite_blocks.cdl_composite_blocks:
                node_type = self.available_node_types["block_composite"]
            else:
                node_type = self.available_node_types["fb_instance"]

        # Program
        elif ("@type" in node.keys()) and (node["@type"] == "S231P:Block"):
            node_type = self.available_node_types["program"]

        # User-defined composite block
        else:
            node_type = self.available_node_types["user_defined_composite_block"]

        return node_type

    def print_all_node_types(self):
        for node in self.cxf_graph:
            print("node", node)
            print("type", self.check_jsonld_graph_node_type(node))

    @property
    def multi_input_blocks(self):
        if self._multi_input_blocks is None:
            self.get_multi_input_blocks()
        return self._multi_input_blocks

    def get_multi_input_blocks(self):
        """
        read file with multi inputs blocks
        """

        self._multi_input_blocks = []
        with open("xml_templates/multInBlocks.txt") as f:
            for line in f:
                self._multi_input_blocks.append(line.strip().replace(".", "_"))

    def load_jsonld(self, file_path):
        """
        loads the JSON-LD
        """

        if '_renamed' in file_path.name:
            file_path = Path(str(file_path).replace('_renamed', ''))

        with open(file_path, "r", encoding="utf-8") as file:

            json_data = json.load(file)

        if self.debug:
            print('jsonld:', json_data)
            print(type(json_data))

        # check conflict of instance and class name
        for node in json_data['@graph']:
            if 'S231P:label' in node.keys():
                print(node)
                class_name = node['@type'].split('.')[-1]
                instance_name = node['S231P:label']
                print('instance name', instance_name)
                print('class name', class_name)

                if instance_name.lower() == class_name.lower():

                    print('Instance name identical to class name. Has to be renamed.')

                    # Convert JSON data to strin
                    json_str = json.dumps(json_data)

                    # Replace the target string
                    json_str = json_str .replace(instance_name, instance_name + '_renamed')

                    # Convert back to JSON object
                    json_data = json.loads(json_str)

                    if self.debug:
                        print('renamed jsonld:', json_data)

            # print(self.check_jsonld_graph_node_type(node))

        return json_data

    @property
    def cxf_graph(self):
        if self.jsonld is None:
            self.load_jsonld()
        if self._cxf_graph is None:
            self.extract_cxf_graph()
        return self._cxf_graph

    def extract_cxf_graph(self):
        """
        extracts the graph from the cxf
        """

        self._cxf_graph = self.jsonld["@graph"]

    @property
    def cxf_instances(self, debug=True):
        if self._cxf_graph is None:
            self.cxf_graph()
        if self._cxf_instances is None:
            self.map_function_block_instances_to_classes()
        return self._cxf_instances

    def map_function_block_instances_to_classes(self):
        """
        Maps function block instances to corresponding classes in a dict
        """

        # empty dict
        self._cxf_instances = self._cxf_instances = {}

        # loop over nodes in graph
        for node in self.cxf_graph:
            if "@type" in node.keys():
                class_string_split = node["@type"].split("#")
                class_string_prefix = class_string_split[0]

                block_instance_name = node["S231P:label"]

                if self.debug:
                    print('class string after split', class_string_split)

                # case: node is a CDL block
                if class_string_prefix == "https://data.ashrae.org/S231P":
                    class_name = self.get_class_name_from_cdl_block(node)
                    self.cxf_instances[block_instance_name] = class_name

                # case: node is not a CDL block
                elif class_string_prefix == 'http://example.org':
                    class_name = self.get_class_name_from_user_defined_composite_block(node)
                    self.cxf_instances[block_instance_name] = class_name

        if self.debug:
            print('cxf_instances', self.cxf_instances)

    # def check_nodes(self):
    #     """
    #     Check nodes
    #     """
    #
    #     if self.debug:
    #         for node in self._cxf_json["@graph"]:
    #             print(node)
    #             print(self.check_node_type(node), "\n")
    #         # print(json.dumps(cxf_dict, indent = 4, sort_keys=False))

    def get_connection_params(
            self,
            connections,
            return_keys=None,
            debug=True,
    ):
        """
        this function checks the connection object
        """

        if return_keys is None:
            return_keys = [
                "source_block_instance",
                "source_block_connector",
                "id",
                "source_block_connector_data_type",
            ]

        # put in list if only one connection
        # handling case with multiple output connections?
        if not isinstance(connections, list):

            if debug:
                print('Connection is not a list. Put into a list for consistency.')

            connections = [connections]

        if debug:
            print("Connections:", connections)

        def get_parameters_of_connection(connection, debug=True):
            """

            """

            if debug:
                print('retrieving information of connector:', connection)

            split = connection.split(".")
            function_block_instance_name = split[0]
            len_split = len(split)

            # get jsonld node of function block instance

            if debug:
                print("split: ", split)
                print("function block instance name: ", function_block_instance_name)
                print("len_split: ", len_split)

            if debug:
                print("show local IDs", self.xml_local_ids)

            # look up XML local ID of corresponding function block instance
            connection_id = self.xml_local_ids[function_block_instance_name]

            # look up x-y-coordinates of corresponding function block instance
            # x_function_block_instance, y_function_block_instance, _, _ =
            # x_function_block_instance = self.program_fb_instances[function_block_instance_name]['x']
            # print(12, x_function_block_instance)

            if debug:
                print("connection ID", connection_id)

            if len_split < 2:
                if debug:
                    print("len_split < 2")

                connection = {
                    "source_block_instance": function_block_instance_name,
                    "source_block_connector": "",
                    "id": connection_id,
                    "source_block_connector_data_type": "REAL",
                }

            else:
                if debug:
                    print("len_split >= 2")

                link = split[1].replace("%", "")

                # get CDL block class name
                class_name = self.get_cdl_block_class_name(function_block_instance_name, debug=debug)

                if debug:
                    print('class_name: ', class_name)

                # replace CDL IOs with IEC IOs if necessary
                if class_name in self.dict_assign_cdl_to_iec_standard_lib:
                    link = self.dict_assign_cdl_to_iec_standard_lib[class_name]['mapping_ios'][link]

                # look up ID
                connection = {
                    "source_block_instance": function_block_instance_name,
                    "source_block_connector": link,
                    "id": connection_id,
                    "source_block_connector_data_type": "REAL",
                }

            # limit return keys to selection
            connection = {
                key: connection[key] for key in return_keys
            }

            return connection

        connections_with_parameters = [get_parameters_of_connection(x, debug=debug) for x in connections]

        if debug:
            print("connections_with_parameters", connections_with_parameters)

        return connections_with_parameters

    def create_dict_connections(self):
        """
        Creates a dict with connections.
        Takes information from the JSONLD about connections.
        Assigns this information to corresponding parts in the XML.
        """

        print("Creating dict with connections")

        # instantiate connections dict from raw connection structure
        self._dict_connections = self._cxf_connection_structure

        if self.debug:
            print('Initial dict with connections:', self._dict_connections)

        # step 1: identify and add all regular connections
        # use only those nodes that are connections or inputs
        connection_and_input_nodes = self.select_jsonld_graph_nodes_by_types(
            [
                self.available_node_types["connection"],
                self.available_node_types["input_real"],
                self.available_node_types["input_bool"],
            ],
            debug=False,
        )

        # loop over JSON nodes of types 'connection' and 'input'
        for count, node in enumerate(connection_and_input_nodes):

            if self.debug:
                print(f"Status _dict_connections at the beginning of iteration {count+1}:", self._dict_connections)
                print("JSON node with connection or input:", node)

            # check the node type
            node_type = self.check_jsonld_graph_node_type(node, debug=False)

            if self.debug:
                print("JSON node type:", node_type)

            # gather information about connection source
            connection_source_instance_id = '.'.join(self.get_instance_name_from_node(node, debug=True))

            if self.debug:
                print("Source connector of the connection:", connection_source_instance_id)

            # get information about connection source
            dict_connection_source_parameters = self.get_connection_params(connection_source_instance_id, debug=False)[0]

            if self.debug:
                print("Dict connection source parameters:", dict_connection_source_parameters)

            # gather information for "to connection"
            to_connected_link_key = node["S231P:isConnectedTo"]

            if self.debug:
                print("Target connector(s) dict:", to_connected_link_key)

            to_connection = None
            if isinstance(to_connected_link_key, dict):
                to_connection = [".".join(self.get_instance_name_from_node(to_connected_link_key))]
            elif isinstance(to_connected_link_key, list):
                to_connection = [".".join(self.get_instance_name_from_node(x)) for x in to_connected_link_key]
            else:
                raise ValueError("to_connected_link_key must be either a dict or a list.")

            if self.debug:
                print("Target connector(s): ", to_connection)

            to_connection_params = self.get_connection_params(to_connection, debug=False)#[0]

            if self.debug:
                print("to_connection_params:", to_connection_params)
                print("_dict_connections before writing information:", self._dict_connections)

            # write inputs
            # loop over connections
            for connection in to_connection_params:

                # Case: the connection links to an output
                if connection["source_block_instance"] in self.cxf_outputs:

                    if self.debug:
                        print('This connection links to an output')

                    # input_link = "y"

                    self._dict_connections[connection["source_block_instance"]]["input"] = dict_connection_source_parameters

                # Case: Connection does not link to on output
                else:
                    print('this connection does not link to an output')
                    input_link = connection["source_block_connector"]
                    # if node_type == self.available_node_types["fb_instance_iec"]:
                    #     print('hallo')
                    #     input_link = self.dict_assign_cdl_to_iec_standard_lib[self.strip_fb_name_from_type(node)]['mapping_ios'][input_link]

                    if self.debug:
                        print('input_link', input_link)

                    self._dict_connections[connection["source_block_instance"]]["input"][input_link] = dict_connection_source_parameters

            # write output connections of blocks
            # do that only for connection nodes
            if node_type == self.available_node_types["connection"]:
                source_block_instance = dict_connection_source_parameters["source_block_instance"]
                self._dict_connections[source_block_instance]["output"][dict_connection_source_parameters["source_block_connector"]] = to_connection_params

            if self.debug:
                print("_dict_connections after writing information: ", self._dict_connections)

        # step 2: add connections from parameter inputs
        if self.debug:
            print('Loop over parameters.')

        # loop over all parameter assignments
        for node in self.select_jsonld_graph_nodes_by_types([self.available_node_types["parameter_definition"]]):

            if self.debug:
                print("node with parameter assignment:", node)

            function_block_instance, parameter = self.get_instance_name_from_node(node)
            parameter_value = node['S231P:value']
            parameter_value_str = self.check_parameter_string(parameter_value)
            parameter_link_id = self.xml_local_ids[parameter_value_str]

            if self.debug:
                print("function_block_instance", function_block_instance)
                print("parameter", parameter)
                print("parameter_value", parameter_value)
                print("parameter_value_str", parameter_value_str)
                print("parameter_link_id", parameter_link_id)

            # find the matching input
            self._dict_connections[function_block_instance]["input"][parameter] = {
                "id": parameter_link_id,
                "source_block_connector": "",
                "type": "REAL",
            }

        if self.debug:
            print("Final dict with connections:", self._dict_connections)

        return self._dict_connections

    def get_program_name(self):
        """
        get program name
        """

        self._program_name = self.select_jsonld_graph_nodes_by_types(
            [self.available_node_types["program"]],
        )[0]["@id"].split("#")[-1].split(".")[-1]

        # rename to avoid conflict with IEC standard function block names
        if self._program_name in iec_standard_function_names.iec_standard_function_names:
            self._program_name_iec = self._program_name + '_renamed'
        else:
            self._program_name_iec = self._program_name

        if self.debug:
            print("program_name", self._program_name)

    @property
    def program_name(self):
        if self._program_name is None:
            self.get_program_name()
        return self._program_name

    def create_dicts_for_jinja(self):
        """
        Creates dictionaries for example with inputs, outputs, function block instances as input for jinja
        """

        print('Creating dicts for jinja.')

        # dict with program inputs
        self.program_inputs = {}

        # dict with program outputs
        self.program_outputs = {}

        # dict with CDL function block instances
        self.program_fb_instances = {}

        # dict with IEC function block instances
        self.program_fb_instances_iec = {}

        # dict with user-defined composite function block instances
        self.program_user_defined_composite_blocks = {}

        # dict with CDL composite function block instances
        self.program_fb_instances_block_composite = {}

        # select node types
        dict_select = self.select_jsonld_graph_nodes_by_types(
            [
                self.available_node_types["input_real"],
                self.available_node_types["input_bool"],
                self.available_node_types["input_int"],
                self.available_node_types["output_real"],
                self.available_node_types["output_bool"],
                self.available_node_types["output_int"],
                self.available_node_types["fb_instance"],
                self.available_node_types["fb_instance_iec"],
                self.available_node_types["user_defined_composite_block"],
                self.available_node_types["block_composite"],
            ]
        )

        # loop over selected node types
        # identify the node types
        # assign the information to the dicts above
        for i, node in enumerate(dict_select):

            type_node = self.check_jsonld_graph_node_type(node)
            block_instance_name = self.get_instance_name_from_node(node)[-1]

            if self.debug:
                print("node:", node)
                print("type:", type_node)
                print("block instance name:", block_instance_name)

            x, y, _, _ = self.get_graph_info(node)
            local_id = self.xml_local_ids[block_instance_name]

            if type_node == self.available_node_types["input_real"]:

                # write entry
                self.program_inputs[block_instance_name] = {
                    "type": "REAL",
                    "localId": local_id,
                    # "connectedTo": connectedTo,
                    "x_absolute": x,
                    "y_absolute": -y,
                    "width": self.calc_block_width(block_instance_name),
                    "height": self.io_height,
                }

            if type_node == self.available_node_types["input_bool"]:

                # write entry
                self.program_inputs[block_instance_name] = {
                    "type": "BOOL",
                    "localId": local_id,
                    # "connectedTo": connectedTo,
                    "x_absolute": x,
                    "y_absolute": -y,
                    "width": self.calc_block_width(block_instance_name),
                    "height": self.io_height,
                }

            if type_node == self.available_node_types["input_int"]:

                # write entry
                self.program_inputs[block_instance_name] = {
                    "type": "INT",
                    "localId": local_id,
                    # "connectedTo": connectedTo,
                    "x_absolute": x,
                    "y_absolute": -y,
                    "width": self.calc_block_width(block_instance_name),
                    "height": self.io_height,
                }

            elif type_node == self.available_node_types["output_real"]:

                dict_inputs = self._dict_connections[block_instance_name]["input"]

                if self.debug:
                    print('case: node is real output:', dict_inputs)

                # write entry
                self.program_outputs[block_instance_name] = {
                    "type": "REAL",
                    "localId": local_id,
                    "x_absolute": x,
                    "y_absolute": -y,
                    "width": self.calc_block_width(block_instance_name),
                    "height": self.io_height,
                    "input_connector": dict_inputs,
                }

            elif type_node == self.available_node_types["output_bool"]:

                dict_inputs = self._dict_connections[block_instance_name]["input"]

                # write entry
                self.program_outputs[block_instance_name] = {
                    "type": "BOOL",
                    "localId": local_id,
                    'x_absolute': x,
                    "y_absolute": -y,
                    "width": self.calc_block_width(block_instance_name),
                    "height": self.io_height,
                    "input_connector": dict_inputs,
                }

            elif type_node == self.available_node_types["output_int"]:

                dict_inputs = self._dict_connections[block_instance_name]["input"]

                # write entry
                self.program_outputs[block_instance_name] = {
                    "type": "INT",
                    "localId": local_id,
                    "x_absolute": x,
                    "y_absolute": -y,
                    "width": self.calc_block_width(block_instance_name),
                    "height": self.io_height,
                    "input_connector": dict_inputs,
                }

            elif type_node == self.available_node_types["fb_instance"]:

                block_class_name = self.get_class_name_from_cdl_block(node)

                dict_inputs = self._dict_connections[block_instance_name]["input"]
                dict_outputs = self._dict_connections[block_instance_name]["output"]

                if self.debug:
                    print('Case: function block instance. Dict with inputs:', dict_inputs)
                    print('Case: function block instance. Dict with dict_outputs:', dict_inputs)

                max_number_inputs_or_outputs = max(len(dict_inputs), len(dict_outputs))

                # write entry
                self.program_fb_instances[block_instance_name] = {
                    "ClassName": block_class_name,
                    "type": "derived name='{}'".format(block_class_name),
                    "localId": local_id,
                    "x_absolute": x,
                    "y_absolute": -y,
                    # "width": self.calc_block_width([block_instance_name, block_class_name]),
                    "width": self.calc_block_width(block_class_name),
                    "height": self.calc_block_height(max_number_inputs_or_outputs),
                    "inputs": dict_inputs,
                    "outputs": dict_outputs  # dictConnections[typeName]["output"],
                }

            elif type_node == self.available_node_types["block_composite"]:

                block_class_name = self.get_class_name_from_cdl_block(node)

                dict_inputs = self._dict_connections[block_instance_name]["input"]
                dict_outputs = self._dict_connections[block_instance_name]["output"]

                if self.debug:
                    print('Case: function block instance. Dict with inputs:', dict_inputs)
                    print('Case: function block instance. Dict with dict_outputs:', dict_inputs)

                max_number_inputs_or_outputs = max(len(dict_inputs), len(dict_outputs))

                # write entry
                self.program_fb_instances_block_composite[block_instance_name] = {
                    "ClassName": block_class_name,
                    "type": "derived name='{}'".format(block_class_name),
                    "localId": local_id,
                    "x_absolute": x,
                    "y_absolute": -y,
                    # "width": self.calc_block_width([block_instance_name, block_class_name]),
                    "width": self.calc_block_width(block_class_name),
                    "height": self.calc_block_height(max_number_inputs_or_outputs),
                    "inputs": dict_inputs,
                    "outputs": dict_outputs  # dictConnections[typeName]["output"],
                }

            elif type_node == self.available_node_types["fb_instance_iec"]:

                block_class_name = self.dict_assign_cdl_to_iec_standard_lib[self.get_class_name_from_cdl_block(node)]['name_iec']

                dict_inputs = self._dict_connections[block_instance_name]["input"]
                dict_outputs = self._dict_connections[block_instance_name]["output"]

                max_number_inputs_or_outputs = max(len(dict_inputs), len(dict_outputs))

                # write entry
                self.program_fb_instances_iec[block_instance_name] = {
                    "ClassName": block_class_name,
                    # "type": "derived name='{}'".format(instance_type),
                    "localId": local_id,
                    "x_absolute": x,
                    "y_absolute": -y,
                    # "width": self.calc_block_width([block_instance_name, block_class_name]),
                    "width": self.calc_block_width(block_class_name),
                    "height": self.calc_block_height(max_number_inputs_or_outputs),
                    "inputs": dict_inputs,
                    "outputs": dict_outputs  # dictConnections[typeName]["output"],
                }

            elif type_node == self.available_node_types["user_defined_composite_block"]:

                block_class_name = self.get_class_name_from_user_defined_composite_block(node)

                dict_inputs = self._dict_connections[block_instance_name]["input"]
                dict_outputs = self._dict_connections[block_instance_name]["output"]

                max_number_inputs_or_outputs = max(len(dict_inputs), len(dict_outputs))

                # write entry
                self.program_user_defined_composite_blocks[block_instance_name] = {
                    "ClassName": block_class_name,
                    "type": "derived name='{}'".format(block_class_name),
                    "localId": local_id,
                    "x_absolute": x,
                    "y_absolute": -y,
                    # "width": self.calc_block_width([block_instance_name, block_class_name]),
                    "width": self.calc_block_width(block_class_name),
                    "height": self.calc_block_height(max_number_inputs_or_outputs),
                    "inputs": dict_inputs,
                    "outputs": dict_outputs  # dictConnections[typeName]["output"],
                }

        if self.debug:
            print("dict_input_vars: ", self.program_inputs)
            print("dict_output_vars: ", self.program_outputs)
            print("dict_fb_instances: ", self.program_fb_instances)

        return self.program_inputs, self.program_outputs, self.program_fb_instances, self.program_fb_instances_iec, self.program_user_defined_composite_blocks, self.program_fb_instances_block_composite

    def render_multi_in_blocks(self, name_block_class, inputs):
        template_loader = jinja2.FileSystemLoader(searchpath="./")
        template_env = jinja2.Environment(loader=template_loader)

        input_str = ", ".join(inputs.keys())
        template_file = "xml_templates/function_blocks/{}.xml".format(name_block_class)
        if self.debug:
            print(template_file)
        template = template_env.get_template(template_file)
        if self.debug:
            print(template)
        output = template.render(
            inputs=inputs,
            input_str=input_str,
        )

        # output text is a string
        if self.debug:
            print(output)

        return output

    def read_and_collect_cdl_block_snippets(self, input_dict):
        """
        creates a dict with python sets for the scalar inputs and the array inputs
        the sets contain the IEC XML snippets
        """

        print('Collecting IEC XML snippets of CDL block classes used.')

        if self.debug:
            print('Input dict', input_dict)

        # # merge regular CDL blocks and CDL blocks from user defined composite blocks
        # dict_all_block_instances = {}
        # dict_all_block_instances.update(self.program_fb_instances)
        # dict_all_block_instances.update(self.program_user_defined_composite_blocks)

        # loop over all function block instances
        for instance_name, instance_attributes in input_dict.items():

            if self.debug:
                print('Block instance name:', instance_name)
                print('Block instance attributes:', instance_attributes)

            cdl_instance_type = instance_attributes["ClassName"]

            # load only those which are not in the IEC library
            if cdl_instance_type in self.dict_map_blocks_to_files.keys():
                files_to_load = self.dict_map_blocks_to_files[cdl_instance_type]
                if self.debug:
                    print('Block instance type:', cdl_instance_type)
                    print('Files to load:', files_to_load)

                for file in files_to_load:
                    with open("xml_templates/function_blocks/{}.xml".format(file), "r") as fileBlock:
                        cdl_block = fileBlock.read()
                    self.dict_xml_snippets_of_cdl_block_classes["scalar_inputs"].add(cdl_block)

        # return self.dict_xml_snippets_of_cdl_block_classes

    # def read_and_append_cdl_block_snippets(self, instance_name, instance_attributes):

    def translate_user_defined_composite_block(self, class_name):

        template_loader = jinja2.FileSystemLoader(searchpath="./")
        template_env = jinja2.Environment(loader=template_loader)

        # fileTemplateVariable = "templateVariable.xml"
        file_template_global = "xml_templates/structure/UserDefinedCompositeBlock.xml"

        # load template
        template = template_env.get_template(file_template_global)

        # render template
        # create output text
        output_text = template.render(
            pouType='functionBlock',
            dictInputVars=self.program_inputs,
            dictOutputVars=self.program_outputs,
            dictParameters=self._program_parameters,
            name=class_name,
            dictFunctionBlockInstances=self.program_fb_instances,
            dictFunctionBlockInstancesIEC=self.program_fb_instances_iec,
            dictCdlBlocks=self.dict_xml_snippets_of_cdl_block_classes,
            user_defined_composite_blocks=self.program_user_defined_composite_blocks,
        )

        # pretty print
        xml_export = xml.dom.minidom.parseString(output_text)
        xml_export = xml_export.toprettyxml()

        with open(
                "plc.xml",
                "w",
                encoding="utf-8",
                newline="\n",
        ) as outfile:
            outfile.write(xml_export)

        return output_text

    def translate(self, debug=False):
        """
        Render template based on dicts with inputs, outputs, blocks etc.
        """

        template_loader = jinja2.FileSystemLoader(searchpath="./")
        template_env = jinja2.Environment(loader=template_loader)

        # fileTemplateVariable = "templateVariable.xml"
        file_template_global = "xml_templates/structure/Global_beremiz.xml"

        if debug:
            print('cwd: ', os.getcwd())

        # load template
        template = template_env.get_template(file_template_global)

        # check if user defined composite blocks are present
        # these have to be rendered
        if self.program_user_defined_composite_blocks:

            print('These user defined composite blocks have to be rendered:', self.program_user_defined_composite_blocks.keys())

            # loop over user defined composite blocks
            # create XML snippet for each composite block and append to dict
            for user_defined_composite_block_instance, values in self.program_user_defined_composite_blocks.items():

                # Compose file name of user-defined composite block
                file = self.jsonld_directory / (user_defined_composite_block_instance + '.jsonld')

                if self.debug:
                    print('jsonld file name of user def comp block:', file)

                # Load JSON-LD file of user-defined function block snippet
                composite_block_jsonld = self.load_jsonld(file)

                if self.debug:
                    print('jsonld of user def comp block:', composite_block_jsonld)

                # instantiate translator class
                file_instance = Cdl2Plc(file, debug=self.debug)

                print(f'Print class variables of {file_instance._program_name}')

                for variable, value in file_instance.__dict__.items():
                    print(f"{variable}: {value}")

                # get CDL classes and collect XML snippets
                self.read_and_collect_cdl_block_snippets(file_instance.program_fb_instances)
                
                # translate JSON-LD of user-defined composite block to XML snippet
                user_defined_composite_block_xml_snippet = file_instance.translate_user_defined_composite_block(values['ClassName'])

                print('XML snippet of user defined composite block', user_defined_composite_block_xml_snippet)

                # append to list
                self.user_defined_composite_block_xml_snippets.append(user_defined_composite_block_xml_snippet)

        # render template
        # create output text
        self.output_text = template.render(
            pouType='program',
            dictInputVars=self.program_inputs,
            dictOutputVars=self.program_outputs,
            dictParameters=self._program_parameters,
            programs=[self._program_name_iec],
            dictFunctionBlockInstances=self.program_fb_instances,
            dictFunctionBlockInstancesComposite=self.program_fb_instances_block_composite,
            dictFunctionBlockInstancesIEC=self.program_fb_instances_iec,
            dictCdlBlocks=self.dict_xml_snippets_of_cdl_block_classes,
            program_user_defined_composite_blocks=self.program_user_defined_composite_blocks,
            user_defined_composite_block_xml_snippets=self.user_defined_composite_block_xml_snippets,
        )

        # print output text as string
        # if False:
        #     with open("outputText.txt", "w") as outfile:
        #         outfile.write(self.output_text)

        # pretty print
        xml_export = xml.dom.minidom.parseString(self.output_text)
        xml_export = xml_export.toprettyxml()

        if False:
            print('Show XML:', xml_export)

        # set output directory
        if self.output_folder is not None:
            directory = self.output_folder / Path('IEC61131-10XML') / Path(self._program_name)
        else:
            directory = Path('IEC61131-10XML') / Path(self._program_name)
        if os.path.exists(directory):
            shutil.rmtree(directory)
        os.makedirs(directory)

        # Writing to sample.json
        with open(
                "{}/plc.xml".format(directory),
                "w",
                encoding="utf-8",
                newline="\n",
        ) as outfile:
            outfile.write(xml_export)

        for variable, value in self.__dict__.items():
            print(f"{variable}: {value}")

        shutil.copyfile('xml_templates/structure/beremiz.xml', Path(directory) / 'beremiz.xml' )


if __name__ == "__main__":  # pragma: no cover

    cxf_json = [
        'cxf/ModelicaTestCases/SingleBlocks/Reals/Add.jsonld',
        "C:/Workdir/Develop/projects/CDL-PLC/paper/cxf/RbcPvt.jsonld",
        "C:/Workdir/Develop/projects/CDL-PLC/paper/cxf/RbcPasCoo.jsonld",
        "C:/Workdir/Develop/projects/CDL-PLC/paper/cxf/RbcAshpModulating.jsonld",
        "C:/Workdir/Develop/projects/CDL-PLC/paper/cxf/RbcAshpGshpModulating.jsonld",
        "C:/Workdir/Develop/projects/CDL-PLC/paper/cxf/RbcGshpModulating.jsonld",
        "C:/Workdir/Develop/projects/CDL-PLC/paper/cxf/RbcHeatingCurve.jsonld",
        "C:/Workdir/Develop/projects/CDL-PLC/paper/cxf/PID.jsonld",
        "C:/Workdir/Develop/projects/CDL-PLC/translator/cdl-plc/cxf/ModelicaTestCases/SingleBlocks/Reals/MultiplyByParameter_1.jsonld",
        "C:/Workdir/Develop/projects/CDL-PLC/translator/cdl-plc/cxf/ModelicaTestCases/SingleBlocks/Reals/MultiplyByParameter_2.jsonld",
        "C:/Workdir/Develop/projects/CDL-PLC/translator/cdl-plc/cxf/ModelicaTestCases/CompositeBlocks/CustomPWithLimiter.jsonld",
        ][-7]

    Cdl2Plc(
        cxf_json,
        debug=True,
    ).translate()
