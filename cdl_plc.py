import json
import jinja2
import xml.dom.minidom
import os
import shutil
import ast


import os

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
print(dname)
os.chdir(dname)


class Cdl2Plc:

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
    }

    dict_CDL_to_OSCAT = {
        "CDL_Reals_PID": "CTRL_PID"
    }

    dict_map_blocks_to_files = {
        "Reals_Add": ["Reals_Add"],
        "Reals_Min": ["Reals_Min"],
        "Reals_MultiplyByParameter": ["Reals_MultiplyByParameter"],
    }

    available_node_types = {
        "parameter_assignment": 1,
        "parameter_definition": 2,
        "connection": 3,
        "fb_instance": 4,
        "fb_instance_iec": 5,
        "output_real": 6,
        "output_bool": 7,
        "input_real": 8,
        "input_bool": 9,
        "program": 10,
    }

    def __init__(
            self,
            cxf_file,
            output_folder=None,
            debug=False,
    ):
        self.cxf_file = cxf_file
        self.output_folder = output_folder

        # properties
        self._multi_input_blocks = None
        self._cxf = None
        self._cxf_graph = None
        self._cxf_instances = None

        self._cxf_connection_structure = None

        self.cxf_blocks = None
        self.cxf_outputs = None

        self._xml_local_ids = None

        self.program_parameters = None

        self._dict_connections = None

        self.program_inputs = None
        self.program_outputs = None
        self.program_fb_instances = None
        self.program_fb_instances_iec = None
        self.dict_cdl_blocks = None

        self.output_text = None
        self._program_name = None

        # self._global_xy_shift = None
        self._x_shift = None
        self._y_shift = None

        self.debug = debug

    # @staticmethod
    def strip_node_id_string(self, node):
        stripped_node_id_string = node["@id"].split("{}.".format(self.program_name))[-1].split(".")
        # if self.debug:
        #     print('stripped_node_id_string: ', stripped_node_id_string)
        return stripped_node_id_string

    @staticmethod
    def strip_fb_name_from_type(node, debug=True):
        stripped = '_'.join(node["@type"].split("#")[-1].split(".")[4:])
        if debug:
            print('stripped: ', stripped)
        return stripped

    @property
    def xml_local_ids(self):
        if self._xml_local_ids is None:
            self.create_xml_local_ids()
        return self._xml_local_ids

    def get_block_class_name(self, instance_name):
        cxf_instances = self.cxf_instances
        print('cxf_instances', cxf_instances)
        test = cxf_instances[instance_name]
        output = test.replace(".", "_")
        return output

    def create_xml_local_ids(self, debug=True):
        """
        create dict with local Ids
        """

        self._xml_local_ids = {}
        local_id = 1

        # loop over JSON-LD
        for i, node in enumerate(self.cxf_graph):
            if debug:
                print("i-iterator and node:", i, node)
            node_type = self.check_node_type(node, debug=debug)
            if debug:
                print("node_type:", node_type)
            if node_type in [
                self.available_node_types["fb_instance"],
                self.available_node_types["fb_instance_iec"],
                self.available_node_types["input_real"],
                self.available_node_types["input_bool"],
                self.available_node_types["output_real"],
                self.available_node_types["output_bool"],
            ]:
                node_label = node["S231P:label"]
                self._xml_local_ids[node_label] = local_id

                local_id += 1
        print("xml_local_ids", self._xml_local_ids)

        # loop over parameters separetly
        # parameters can not be taken from the JSON-LD directly
        list_parameters = [
            self.check_parameter_string(x['S231P:value']) for x in
            self.group_node_types([self.available_node_types["parameter_assignment"]])
        ]
        if self.debug:
            print("list_parameters", list_parameters)

        for par in list_parameters:
            self.xml_local_ids[par] = local_id
            local_id += 1

        if self.debug:
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
            scale_factor_x = 6
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

        if isinstance(value, int):
            par_str = "r{}".format(value)
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
            print("\ncheck_node:", check_node)

        output = self.strip_node_id_string(check_node)
        if self.debug:
            print("output", output)
        if len(output) == 2:
            instance, link = output
        else:
            instance = output[0]
            link = ""
        if self.debug:
            print("instance:", instance)
            print("link:", link)
        output = {"instance": instance, "link": link}
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
            print("\ninput_structure", input_structure)
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

    def create_xml_parameters(self, debug=True):
        """
        creates a dict with local parameters
        """
        self.program_parameters = {}
        for node in self.cxf_graph:
            node_type = self.check_node_type(node)
            if node_type == 1:
                if debug:
                    print("node with parameter:", node)

                def extract_parameter_value(node):
                    # extract parameter value
                    node_value_local = node['S231P:value']
                    if debug:
                        print("node_value", node_value_local)

                    if isinstance(node_value_local, int):
                        if debug:
                            print('The parameter is an integer')
                        parameter_value_local = node_value_local
                        parValueType = "REAL"
                    else:
                        if debug:
                            print('The parameter is a variable / input')

                        # find the corresponding value

                        nodes_with_parameter_definitions = self.group_node_types(
                                [2],
                        )
                        if debug:
                            print('nodes_with_parameter_definitions:', nodes_with_parameter_definitions)
                        for nodeParDef in nodes_with_parameter_definitions:
                            if debug:
                                print('nodeParDef:', nodeParDef)
                            if nodeParDef["S231P:label"] == node_value_local:
                                parameter_value_local = nodeParDef["S231P:value"]
                    parameter_value_local = "{:.1f}".format(parameter_value_local)
                    if self.debug:
                        print("parameter_value", parameter_value_local)
                    return node_value_local, parameter_value_local

                node_value, parameter_value = extract_parameter_value(
                    node,
                )

                instance = self.parse_id_key(node)["instance"]
                link = self.parse_id_key(node)["link"]
                if self.debug:
                    print("instance", instance)
                    print("link", link)

                def get_local_id():
                    par_str = self.check_parameter_string(node_value)
                    local_id = self.xml_local_ids[par_str]
                    return par_str, local_id

                par_str, local_id = get_local_id()

                if self.debug:
                    print(par_str)
                self.program_parameters[par_str] = {
                    "instance": instance,
                    "link": link,
                    "value": parameter_value,
                    "valueType": "REAL",
                    "localId": local_id,
                }

    @property
    def cxf_connection_structure(self):
        if self._cxf_connection_structure is None:
            self.create_cxf_connection_structure()
        return self._cxf_connection_structure

    def create_cxf_connection_structure(self):
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

        dict_input = self.group_node_types([self.available_node_types["program"]])[0]

        self._cxf_connection_structure = {}

        if self.debug:
            print("\ndict_input", dict_input)
            # print("node[S231P:containsBlock]", node["S231P:containsBlock"])

        # detect blocks
        self.cxf_blocks = self.extract_id_instance(
            dict_input["S231P:containsBlock"],
        )

        if self.debug:
            print("\nblocks:", self.cxf_blocks)

        # from_block = node["@id"].split("#")[-1].split(".")[0]

        for block in self.cxf_blocks:
            self._cxf_connection_structure[block] = {"input": {}, "output": {}}
        if self.debug:
            print("\ndict_connections:", self._cxf_connection_structure)

        # detect outputs
        self.cxf_outputs = self.extract_id_instance(
            dict_input["S231P:hasOutput"],
        )
        if self.debug:
            print("\noutputs:", self.cxf_outputs)

        for output in self.cxf_outputs:
            self._cxf_connection_structure[output] = {"input": {}}
        if self.debug:
            print("\ndict_connections:", self._cxf_connection_structure)
            print("\ncxf_blocks:", self.cxf_blocks)
            print("\ncxf_outputs:", self.cxf_outputs)

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

    def group_node_types(
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

        print('group node types')

        if node_types is []:
            node_types = self.available_node_types
        list_return = []
        for node in self.cxf_graph:
            if debug:
                print("node", node)
            node_type = self.check_node_type(node)
            if self.debug:
                print("node_type", node_type)
            if node_type in node_types:
                list_return.append(node)
        return list_return

    def check_node_type(self, node, debug=False):
        """
        This function checks the type of a node of the cxf graph
        """

        if debug:
            print("node:", node)
        keys = list(node.keys())

        if debug:
            print('set keys:', set(keys))

        node_type = None

        if set(keys).issubset({"@id", "S231P:isFinal", "S231P:value"}):
            # this is a parameter of a block

            # get instance name
            instance_name = node["@id"].split("#")[-1].split(".")[-2]
            if debug:
                print('instance_name:', instance_name)
            # get class name
            class_name = self.get_block_class_name(instance_name)

            # if self.debug:
            #     print("instance_name", instance_name)
            #     print("class_name", class_name)

            if class_name in self.multi_input_blocks:
                node_type = self.available_node_types["nin_fb_instance"]
            else:
                node_type = self.available_node_types["parameter_assignment"]

        elif keys == [
            "@id",
            "@type",
            "S231P:accessSpecifier",
            "S231P:description",
            "S231P:isOfDataType",
            "S231P:label",
            "S231P:value",
        ]:
            node_type = self.available_node_types["parameter_definition"]

        elif keys == ["@id", "S231P:isConnectedTo"]:
            check_is_connected_to_keys = node["S231P:isConnectedTo"]
            id_key_only = None
            if isinstance(check_is_connected_to_keys, list):
                # check if "@id" is the only key
                # set_check = set()
                if all([list(x.keys()) == ["@id"] for x in check_is_connected_to_keys]):
                    id_key_only = True

            elif isinstance(check_is_connected_to_keys, dict):
                if list(node["S231P:isConnectedTo"].keys())[0] == "@id":
                    id_key_only = True
            if id_key_only:
                node_type = self.available_node_types["connection"]

        elif node["@type"] == "S231P:RealOutput":
            node_type = self.available_node_types["output_real"]

        elif node["@type"] == "S231P:BooleanOutput":
            node_type = self.available_node_types["output_bool"]

        elif node["@type"] == "S231P:RealInput":
            node_type = self.available_node_types["input_real"]

        elif node["@type"] == "S231P:BooleanInput":
            node_type = self.available_node_types["input_bool"]

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

            fb_name = self.strip_fb_name_from_type(node)
            if debug:
                print("fb_name", fb_name)
            if fb_name in self.dict_assign_cdl_to_iec_standard_lib:
                node_type = self.available_node_types["fb_instance_iec"]
            else:
                node_type = self.available_node_types["fb_instance"]

        elif ("@type" in node.keys()) and (node["@type"] == "S231P:Block"):
            node_type = self.available_node_types["program"]

        else:
            node_type = None

        return node_type

    def print_all_node_types(self):
        for node in self.cxf_graph:
            print("\nnode", node)
            print("type", self.check_node_type(node))

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

    @property
    def cxf(self):
        if self._cxf is None:
            self.load_cxf()
        return self._cxf

    def load_cxf(self):
        """
        loads the JSON
        """

        self._cxf = json.load(open(self.cxf_file))

    @property
    def cxf_graph(self):
        if self._cxf is None:
            self.load_cxf()
        if self._cxf_graph is None:
            self.extract_cxf_graph()
        return self._cxf_graph

    def extract_cxf_graph(self):
        """
        extracts the graph from the cxf
        """

        self._cxf_graph = self._cxf["@graph"]

    @property
    def cxf_instances(self, debug=True):
        if self._cxf_graph is None:
            self.cxf_graph()
        if self._cxf_instances is None:
            self.get_cxf_block_instances(debug=debug)
        return self._cxf_instances

    def get_cxf_block_instances(self, debug=False):
        """
        Check function block classes
        """

        self._cxf_instances = {}
        for node in self.cxf_graph:
            if "@type" in node.keys():
                node_type = node["@type"].split("#")
                print('node_type after split', node_type)
                if node_type[0] == "https://data.ashrae.org/S231P":
                    self.cxf_instances[node["S231P:label"]] = self.strip_fb_name_from_type(node)
        if debug:
            print('cxf_instances', self.cxf_instances)

    def check_nodes(self):
        """
        Check nodes
        """

        if self.debug:
            for node in self._cxf_json["@graph"]:
                print(node)
                print(self.check_node_type(node), "\n")
            # print(json.dumps(cxf_dict, indent = 4, sort_keys=False))

    def get_connection_params(
            self,
            connections,
            return_keys=None,
    ):
        """
        this function checks the connection object
        """

        if return_keys is None:
            return_keys = ["block", "link", "id", "type"]

        # put in list if only one connection
        # handling case with multiple output connections?
        if not isinstance(connections, list):
            print('connection is not a list')
            connections = [connections]

        if self.debug:
            print("connections", connections)

        def define_parameters(connection):
            split = connection.split(".")
            block_name = split[0]
            len_split = len(split)
            if self.debug:
                print("\nsplit", split)
                print("len_split", len_split)

            if self.debug:
                print("xml_local_ids", self.xml_local_ids)

            connection_id = self.xml_local_ids[block_name]
            if self.debug:
                print("connection_id", connection_id)

            if len_split < 2:
                if self.debug:
                    print("len_split < 2")
                connection = {
                    "block": block_name,
                    "link": "",
                    "id": connection_id,
                    "type": "REAL",
                }

            else:
                if self.debug:
                    print("len_split >= 2")
                link = split[1].replace("%", "")
                class_name = self.get_block_class_name(block_name)
                print(1, class_name)
                # replace CDL IOs with IEC IOs if necessary
                if class_name in self.dict_assign_cdl_to_iec_standard_lib:
                    link = self.dict_assign_cdl_to_iec_standard_lib[class_name]['mapping_ios'][link]
                # look up ID
                connection = {
                    "block": block_name,
                    "link": link,
                    "id": connection_id,
                    "type": "REAL",
                }

            connection = {
                key: connection[key] for key in return_keys
            }

            return connection

        connections_with_parameters = [define_parameters(x) for x in connections]

        if self.debug:
            print("connections_with_parameters", connections_with_parameters)

        return connections_with_parameters

    @property
    def dict_connections(self):
        if self._dict_connections is None:
            self.create_dict_connections()
        return self._dict_connections

    def create_dict_connections(self):
        """
        Text
        """

        print("\ncreating dict with connections")

        # get only those nodes which are connections or inputs
        connection_and_input_nodes = self.group_node_types([
            self.available_node_types["connection"],
            self.available_node_types["input_real"],
            self.available_node_types["input_bool"],
        ])
        connection_structure = self.cxf_connection_structure

        if self.debug:
            print("connection_structure", connection_structure)
            print("cxf_outputs", self.cxf_outputs)

        self._dict_connections = connection_structure

        # loop over connection and input nodes
        for node in connection_and_input_nodes:

            node_type = self.check_node_type(node)

            if self.debug:
                print("\nnode", node)
                print("node_type", node_type)
                print("Status _dict_connections", self._dict_connections)

            # step 1: all regular connections

            # gather information for "from connection"
            from_connection = '.'.join(self.strip_node_id_string(node))

            dict_from_connection = self.get_connection_params(from_connection)[0]
            if self.debug:
                print("from_connection", from_connection)
                print("dict_from_connection", dict_from_connection)

            # gather information for "to connection"
            to_connected_link_key = node["S231P:isConnectedTo"]
            if self.debug:
                print("\nto_connected_link_key", to_connected_link_key)

            to_connection = None
            if isinstance(to_connected_link_key, dict):
                to_connection = [".".join(self.strip_node_id_string(to_connected_link_key))]
            elif isinstance(to_connected_link_key, list):
                to_connection = [".".join(self.strip_node_id_string(x)) for x in to_connected_link_key]
            else:
                raise ValueError("to_connected_link_key must be either a dict or a list")

            if self.debug:
                print("to_connection: ", to_connection)

            to_connection_params = self.get_connection_params(to_connection)#[0]
            if self.debug:
                print("to_connection_params: ", to_connection_params)
                print("_dict_connections before: ", self._dict_connections)

            # write inputs
            # loop over connections
            for connection in to_connection_params:
                if connection["block"] in self.cxf_outputs:
                    print('this connection links to an output')
                    input_link = "y"
                else:
                    print('this connection does not link to an output')
                    input_link = connection["link"]
                    # if node_type == self.available_node_types["fb_instance_iec"]:
                    #     print('hallo')
                    #     input_link = self.dict_assign_cdl_to_iec_standard_lib[self.strip_fb_name_from_type(node)]['mapping_ios'][input_link]
                if self.debug:
                    print('input_link', input_link)
                self._dict_connections[connection["block"]]["input"][input_link] = dict_from_connection

            # write output connections of blocks
            # do that only for connection nodes
            if node_type == self.available_node_types["connection"]:
                self._dict_connections[dict_from_connection["block"]]["output"][dict_from_connection["link"]] = to_connection_params

            if self.debug:
                print("_dict_connections after: ", self._dict_connections)

        # step 2: add connections from parameter inputs
        # loop over all parameter assignments
        for node in self.group_node_types(
                [self.available_node_types["parameter_assignment"]],
        ):
            if self.debug:
                print("node", node)
            block, parameter = self.strip_node_id_string(node)
            parameter_value = node['S231P:value']
            parameter_value_str = self.check_parameter_string(parameter_value)
            parameter_link_id = self.xml_local_ids[parameter_value_str]
            if self.debug:
                print("block, parameter, parameterValue", block, parameter, parameter_value, parameter_value_str,
                      parameter_link_id)

            # find the matching input

            self.dict_connections[block]["input"][parameter] = {
                "id": parameter_link_id,
                "link": "",
                "type": "REAL",
            }

        if self.debug:
            print("dict_connections", self.dict_connections)

    def get_program_name(self):
        """
        get program name
        """

        self._program_name = self.group_node_types(
            [self.available_node_types["program"]],
        )[0]["@id"].split("#")[-1].split(".")[-1]

        if self.debug:
            print("program_name", self._program_name)

    @property
    def program_name(self):
        if self._program_name is None:
            self.get_program_name()
        return self._program_name

    def create_dicts_for_jinja(self):
        """
        Inputs, outputs, function block instances
        """

        self.program_inputs = {}
        self.program_outputs = {}
        self.program_fb_instances = {}
        self.program_fb_instances_iec = {}

        dict_select = self.group_node_types(
            [
                self.available_node_types["input_real"],
                self.available_node_types["input_bool"],
                self.available_node_types["output_real"],
                self.available_node_types["output_bool"],
                self.available_node_types["fb_instance"],
                self.available_node_types["fb_instance_iec"],
            ]
        )

        for i, node in enumerate(dict_select):
            type_node = self.check_node_type(node)
            type_name = self.strip_node_id_string(node)[-1]
            if self.debug:
                print("\nnode:", node)
                print("type:", type_node)
                print("name:", type_name)

            x, y, width, height = self.get_graph_info(node)
            local_id = self.xml_local_ids[type_name]

            if type_node == self.available_node_types["input_real"]:

                # write entry
                self.program_inputs[type_name] = {
                    "type": "REAL",
                    "localId": local_id,
                    # "connectedTo": connectedTo,
                    "x": x,
                    "y": -y,
                    "width": width,
                    "height": height,
                }

            if type_node == self.available_node_types["input_bool"]:

                # write entry
                self.program_inputs[type_name] = {
                    "type": "BOOL",
                    "localId": local_id,
                    # "connectedTo": connectedTo,
                    "x": x,
                    "y": -y,
                    "width": width,
                    "height": height,
                }

            elif type_node == self.available_node_types["output_real"]:

                dict_inputs = self.dict_connections[type_name]["input"]

                # write entry
                self.program_outputs[type_name] = {
                    "type": "REAL",
                    "localId": local_id,
                    "x": x,
                    "y": -y,
                    "width": width,
                    "height": height,
                    "inputFrom": dict_inputs,
                }

            elif type_node == self.available_node_types["output_bool"]:

                dict_inputs = self.dict_connections[type_name]["input"]

                # write entry
                self.program_outputs[type_name] = {
                    "type": "BOOL",
                    "localId": local_id,
                    "x": x,
                    "y": -y,
                    "width": width,
                    "height": height,
                    "inputFrom": dict_inputs,
                }

            elif type_node == self.available_node_types["fb_instance"]:
                instance_type = self.strip_fb_name_from_type(node)

                dict_inputs = self.dict_connections[type_name]["input"]
                dict_outputs = self.dict_connections[type_name]["output"]

                # write entry
                self.program_fb_instances[type_name] = {
                    "instanceType": instance_type,
                    "type": "derived name='{}'".format(instance_type),
                    "localId": local_id,
                    "x": x,
                    "y": -y,
                    "width": width,
                    "height": height,
                    "inputs": dict_inputs,
                    "outputs": dict_outputs  # dictConnections[typeName]["output"],
                }

            elif type_node == self.available_node_types["fb_instance_iec"]:
                instance_type = self.dict_assign_cdl_to_iec_standard_lib[self.strip_fb_name_from_type(node)]['name_iec']

                dict_inputs = self.dict_connections[type_name]["input"]
                dict_outputs = self.dict_connections[type_name]["output"]

                # write entry
                self.program_fb_instances_iec[type_name] = {
                    "instanceType": instance_type,
                    # "type": "derived name='{}'".format(instance_type),
                    "localId": local_id,
                    "x": x,
                    "y": -y,
                    "width": width,
                    "height": height,
                    "inputs": dict_inputs,
                    "outputs": dict_outputs  # dictConnections[typeName]["output"],
                }

        if self.debug:
            print("\ndict_input_vars: ", self.program_inputs)
            print("\ndict_output_vars: ", self.program_outputs)
            print("\ndict_fb_instances: ", self.program_fb_instances)

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

    def create_dict_cdl_blocks(self):
        """
        creates a dict with sets for the scalar inputs and the array inputs
        the sets contain the IEC XML snippets
        """

        self.dict_cdl_blocks = {
            "scalar_inputs": set(),
            "array_inputs": set(),
        }

        if self.debug:
            print('dict_fb_instances', self.program_fb_instances)

        # loop over all function block instances
        for key, values in self.program_fb_instances.items():
            if self.debug:
                print(key, values)
            cdl_instance_type = values["instanceType"]

            # load only those which are not in the IEC library
            if cdl_instance_type in self.dict_map_blocks_to_files.keys():
                files_to_load = self.dict_map_blocks_to_files[cdl_instance_type]
                if self.debug:
                    print(key, cdl_instance_type, files_to_load)

                for file in files_to_load:
                    with open("xml_templates/function_blocks/{}.xml".format(file), "r") as fileBlock:
                        cdl_block = fileBlock.read()
                    self.dict_cdl_blocks["scalar_inputs"].add(cdl_block)

    def create_iec_xml(self, debug=False):
        """
        Render based on dicts
        """
        template_loader = jinja2.FileSystemLoader(searchpath="./")
        template_env = jinja2.Environment(loader=template_loader)

        # fileTemplateVariable = "templateVariable.xml"
        file_template_global = [
            "xml_templates/structure/Global.xml",
            "templateVariable.xml",
        ][0]

        if debug:
            print('cwd: ', os.getcwd())

        template = template_env.get_template(file_template_global)
        self.output_text = template.render(
            dictInputVars=self.program_inputs,
            dictOutputVars=self.program_outputs,
            dictParameters=self.program_parameters,
            programs=[self.program_name],
            dictFunctionBlockInstances=self.program_fb_instances,
            dictFunctionBlockInstancesIEC=self.program_fb_instances_iec,
            dictCdlBlocks=self.dict_cdl_blocks,
        )

        # print output text as string
        # if False:
        #     with open("outputText.txt", "w") as outfile:
        #         outfile.write(self.output_text)

        xml_export = xml.dom.minidom.parseString(self.output_text)
        xml_export = xml_export.toprettyxml()
        if self.debug:
            print(xml_export)

        if self.output_folder is not None:
            directory = self.output_folder + 'IEC61131-10XML/{}'.format(self._program_name)
        else:
            directory = 'IEC61131-10XML/{}'.format(self._program_name)
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

    def translate(self):
        self.get_global_xy_shift()
        self.create_xml_local_ids()
        self.create_cxf_connection_structure()
        self.create_xml_parameters()
        self.create_dict_connections()
        self.create_dicts_for_jinja()
        self.create_dict_cdl_blocks()

        self.create_iec_xml()

        for variable, value in self.__dict__.items():
            print(f"{variable}: {value}")


if __name__ == "__main__":  # pragma: no cover

    cxf_json = 'cxf/ModelicaTestCases/SingleBlocks/Reals/Add.jsonld'
    Cdl2Plc(cxf_json, debug=True).translate()
