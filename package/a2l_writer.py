from . import asap_template
from .t32auto import T32_Auto
import datetime
from pathlib import Path
import re
import json
from library.colorama import init, Fore, Back, Style
import pickle

class A2L_Writer:
    def __init__(self, c_parser, excel_reader, mapxml, path_strgsysjson, pathinfo,history, a2l_result=None, warning_result=None) -> None:
        def determine_actuator(path_strgsysjson, variant_name):
            with open(path_strgsysjson, 'r') as rd_f: strgsystem = json.load(rd_f)
            return [each for each in strgsystem["actuator"] if each in variant_name][0]
        self.mapxml = mapxml
        self.history = history
        self.excel_reader = excel_reader
        file_name = mapxml.stem.replace(".","_")
        self.A2L_Path = c_parser.target_project / "Build" / f"{file_name}.a2l"
        self.c_parser = c_parser
        self.variant_name = mapxml.stem
        self.actuator_name = determine_actuator(path_strgsysjson, self.variant_name)
        self.warning_lst = []
        self.pickled_exl_info = pickle.dumps(excel_reader.exl_info)
        self.set_A2L_basic_info(pathinfo)
        self.a2l_group_info = excel_reader.a2l_group_info
        self.added_a2l_elements = {}
        self.exl_info = pickle.loads(self.pickled_exl_info)
        self.add_element(pathinfo.project,self.exl_info, validate_mode= False)
        self.add_conv_method()
        self.add_enum_vtab()
        self.add_basic_vtab()
        self.add_group()
        self.A2L_str += self.project_end
        self.write_text(self.A2L_Path, self.A2L_str)
        init(autoreset=True)
        color = ""
      
        
        a2l_result.append({"filename": color+ self.A2L_Path.name,\
            "date": Fore.WHITE + str(datetime.datetime.fromtimestamp(self.A2L_Path.stat().st_mtime)),\
                "warning" : Fore.WHITE + str(len(self.warning_lst)),\
                    "path": Fore.WHITE + self.A2L_Path.absolute().as_posix()}\
                        )
        
        for warning in self.warning_lst:
            warning_result.append({"filename": self.A2L_Path.name,\
            "message" :warning["message"],\
                "symbol" : warning["symbol"]\
                    }\
            )

    

    def add_basic_vtab(self):
        for vtab_name in self.basic_vtab:
            self.A2L_str += self.compu_tab_verb["compu_vtab"].format(
                        conv_name=vtab_name
                    )
        for vtab_name in self.basic_vtab:
            tab_element = ""
            length = len(self.basic_vtab[vtab_name] )
            for element in self.basic_vtab[vtab_name]:
                tab_element += self.tab_element_format_vtab.format(indent = " "*6,\
                    value1 = element,string_repr = self.basic_vtab[vtab_name][element])
            tab_element +="""      DEFAULT_VALUE ""\n"""
            vtab_name+=".Table"
            self.A2L_str += self.item.format(indent = " "*4,\
                                            ID = "COMPU_VTAB",\
                                            ID_NAME = vtab_name,\
                                            comment = '""',\
                                            others = f" TAB_VERB {length}",\
                                            contents=tab_element)
            self.A2L_str += "\n"

    def add_compu_method_vtab_range(self,c_instance):
        vtab_name  = c_instance.name +".CONVERSION"
        self.A2L_str += self.compu_tab_verb["compu_vtab_range"].format(
                conv_name=vtab_name
            )
                    
    def add_table_vtab_range(self, c_instance):
        vtab_name  = c_instance.name +".CONVERSION"
        tab_element = ""

        for element in c_instance.elements:
            tab_element += self.tab_element_format.format(indent = " "*6,\
                    value1 = int(element.enum_val),string_repr = element.name)

        tab_element +="""      DEFAULT_VALUE ""\n"""
        self.A2L_str += self.item.format(indent = " "*4,\
                                        ID = "COMPU_VTAB_RANGE",\
                                        ID_NAME = vtab_name,\
                                        comment = '""',\
                                        others = f" {len(c_instance.elements)}",\
                                        contents=tab_element)
        self.A2L_str += "\n"

    def add_compu_method_vtab(self,c_instance):
        vtab_name  = c_instance.name +".CONVERSION"
        self.A2L_str += self.compu_tab_verb["compu_vtab"].format(
                        conv_name=vtab_name
                )

    def add_table_method_vtab(self,c_instance):
        vtab_name  =c_instance.name +".CONVERSION"
        tab_element = ""
        vtab_name+=".Table"
        
        for element in c_instance.elements:
            tab_element += self.tab_element_format_vtab.format(indent = " "*6,\
                value1 = int(element.enum_val),string_repr = element.name)
        
        tab_element +="""      DEFAULT_VALUE ""\n"""
        self.A2L_str += self.item.format(indent = " "*4,\
                                        ID = "COMPU_VTAB",\
                                        ID_NAME = vtab_name,\
                                        comment = '""',\
                                        others = f" TAB_VERB {len(c_instance.elements)}",\
                                        contents=tab_element)
        self.A2L_str += "\n"

    def add_enum_vtab(self):
        for A2L_Name in self.added_a2l_elements:
            A2L_element = self.added_a2l_elements[A2L_Name]
            c_instance = self.c_parser.symbol_shortcut[A2L_element["SYMBOL_NAME"]]
            if c_instance.IsEnum and not c_instance.IsVecEnum:
                self.add_compu_method_vtab_range(c_instance)
            elif c_instance.IsEnum and c_instance.IsVecEnum:
                self.add_compu_method_vtab(c_instance)
        
        for A2L_Name in self.added_a2l_elements: 
            A2L_element = self.added_a2l_elements[A2L_Name]       
            c_instance = self.c_parser.symbol_shortcut[A2L_element["SYMBOL_NAME"]]
            if c_instance.IsEnum and not c_instance.IsVecEnum:
                self.add_table_vtab_range(c_instance)
            elif c_instance.IsEnum and c_instance.IsVecEnum:
                self.add_table_method_vtab(c_instance)
                
    def add_conv_method(self):
        for compu_method in self.compu_method_infos:
            self.A2L_str += self.compu_linear.format(
                conv_name=compu_method,
                factor=self.compu_method_infos[compu_method]["formula"]["factor"],
            )

    def add_string(self,\
                    var_addr,\
                    var_type, \
                    var_range, \
                    symbol_name,\
                    var_link_type,\
                    a2l_name,
                    comment ="\"\"",\
                    c_instance = None,
        ):
        if self.check_validity(a2l_name,"STRING",symbol_name,c_instance) is False:
            return False
        contents = self.set_content(
            f"ASCII {var_addr} __{var_type}_Z 0 NO_COMPU_METHOD {var_range}"
        )
        contents += self.set_content("ECU_ADDRESS_EXTENSION 0x0")
        contents += self.set_content(f"EXTENDED_LIMITS {var_range}")
        contents += self.set_content(f"NUMBER {c_instance.array_info[0]}")
        contents += self.set_link_map(
            display_range=var_range,
            symbol = symbol_name,
            var_addr=var_addr,
            var_addr_type=var_link_type,
        )

        measure_text = self.set_template_item(
            "CHARACTERISTIC", a2l_name, contents, comment=comment
        )
        self.A2L_str += measure_text
        return True

    def add_group_to_hierachy(self, hierachy, group):
        if group:
            group_head = group.pop(0)
            if group_head not in hierachy:
                hierachy[group_head] = {}
            self.add_group_to_hierachy(hierachy[group_head],group)
    
    def make_grp_str(self, group_name ,sub_group,root = False):
        if root:
            return self.group_root.format(group_name = group_name,sub_group =sub_group,indent1=" "*4,indent2 = " "*6)
        else:
            return self.group.format(group_name = group_name,sub_group =sub_group,indent1=" "*4)
    
    def make_sub_grp_str(self, sub_group_type ,sub_group_elements):
        return self.sub_group.format(sub_group_type= sub_group_type,\
                                    sub_group_elements = sub_group_elements,\
                                        indent1 = " "*6,\
                                        indent2 = " "*8,\
                                        )
    
    def add_group_to_a2l(self,current_stage,group_name,root=False):
        if current_stage:
            root_group_str = ""
            sub_groups = list(current_stage.keys())
            sub_group_str = ""
            sub_elements_by_type = {"REF_CHARACTERISTIC":{}, "REF_MEASUREMENT":{},"SUB_GROUP": {} }
            for sub_element in sub_groups:
                if sub_element in self.added_a2l_elements:
                    if self.added_a2l_elements[sub_element]["A2LTYPE"].upper() == "MEASUREMENT":
                        sub_elements_by_type["REF_MEASUREMENT"][sub_element] = current_stage[sub_element]
                    else:
                        sub_elements_by_type["REF_CHARACTERISTIC"][sub_element] = current_stage[sub_element]
                else:
                    sub_elements_by_type["SUB_GROUP"][sub_element] = current_stage[sub_element]
            for sub_element_type in sub_elements_by_type:
                sub_elements = list(sub_elements_by_type[sub_element_type].keys())
                if not sub_elements:
                    continue
                sub_elements_str = " ".join(sub_elements)
                sub_group_str += self.make_sub_grp_str(sub_element_type,sub_elements_str)
            root_group_str = self.make_grp_str(group_name=group_name,sub_group =sub_group_str,root = root)
            self.A2L_str += root_group_str

    def add_hierachy_to_a2l(self,a2l_hierachy,root = True):
        if a2l_hierachy: 
            for group_name in a2l_hierachy:
                self.add_group_to_a2l(a2l_hierachy[group_name],group_name,root = root)
                self.add_hierachy_to_a2l(a2l_hierachy[group_name],root= False)

    def add_group(self):
        a2l_hierachy = {}
        for a2l_name in self.added_a2l_elements:
            a2l_element = self.added_a2l_elements[a2l_name]
            a2l_element["GROUP"].append(a2l_element["A2L_Name"])
            self.add_group_to_hierachy(a2l_hierachy, a2l_element["GROUP"])
        break_here = []
        self.add_hierachy_to_a2l(a2l_hierachy)

    def search_added(self, input_A2L_Name):
        
        for a2l_element in self.added_a2l_elements:
            if a2l_element == input_A2L_Name:
                return self.added_a2l_elements[a2l_element]
        return False

    def add_axis(self,\
                    var_addr,\
                    var_type, \
                    var_range, \
                    symbol_name,\
                    var_link_type,\
                    a2l_name,
                    comment= "\"\"",\
                    compu_method = "NO_COMPU_METHOD",\
                    c_instance = None,\
                    bit_mask = None\
        ):
        if self.check_validity(a2l_name,"AXIS",symbol_name,c_instance) is False:
            return False
        contents = self.set_content(
            f"{var_addr} NO_INPUT_QUANTITY SSV__{var_type}_S 0 {compu_method} {c_instance.array_info[0]} {var_range}"
        )
        contents += self.set_content("ECU_ADDRESS_EXTENSION 0x0")
        contents += self.set_content(f"EXTENDED_LIMITS {var_range}")
        contents += self.set_content("DEPOSIT ABSOLUTE")
        contents += self.set_link_map(
            display_range=var_range,
            symbol = symbol_name,
            var_addr=var_addr,
            var_addr_type=var_link_type,
        )
        contents += self.set_content('FORMAT "%.3"')
        measure_text = self.set_template_item(
            "AXIS_PTS", a2l_name, contents, comment=comment
        )
        self.A2L_str += measure_text
        return True
    
    def add_map(self,\
                    var_addr,\
                    var_type, \
                    var_range, \
                    symbol_name,\
                    var_link_type,\
                    a2l_name,
                    compu_method = "NO_COMPU_METHOD",
                    comment ="\"\"",\
                    axis = None,
                    c_instance = None,
                    dic_shared_axis = None,
                    bit_shitf =None,
                    bit_mask = None\
        ):
        if self.check_validity(a2l_name,"MAP",symbol_name,c_instance) is False:
            return False
        contents = self.set_content(
                f"MAP {var_addr} __{var_type}_Z 0 {compu_method}  {var_range}"
            )
        # if writable == "READ_ONLY":
        #     contents += self.set_content("READ_ONLY")
        contents += self.set_content("ECU_ADDRESS_EXTENSION 0x0")
        contents += self.set_content(f"EXTENDED_LIMITS {var_range}")
        if len(c_instance.array_info) == 1: # 1차원 배열을 map으로보고싶으면 축하나 추가
            c_instance.array_info.append(1)
        else:
            c_instance.array_info = c_instance.array_info[::-1]
        if not c_instance.IsArray:
            self.warning_lst.append({"message" : "It is not an array cannot make MAP","symbol": f"\"{symbol_name}\""})
            return False
        if dic_shared_axis:
            indextoletter = ["x","y"]
            if len(dic_shared_axis) == 1:
                if list(dic_shared_axis.keys())[0] == "y":
                    c_instance.array_info = c_instance.array_info[::-1]
            for index in range(len(c_instance.array_info)):
                
            # for axis in dic_shared_axis:
                if indextoletter[index] in dic_shared_axis:
                    try:
                        axis_name = dic_shared_axis[indextoletter[index]]["name"]
                        axis_a2l_element = self.search_added(axis_name)
                        if not axis_a2l_element:
                            # print(f"Cannot find axis {axis_name} for {symbol_name}")
                            self.warning_lst.append({"message":f"Cannot find axis {axis_name}", "symbol":f"\"{symbol_name}\""})
                        axis_symbol_name = axis_a2l_element["SYMBOL_NAME"]
                        l_c_instance = self.c_parser.symbol_shortcut[axis_symbol_name]
                        l_range = " ".join(self.a2l_type_info["type_range"][l_c_instance.type])
                    except:
                        axis_name = ""
                    try:
                        if dic_shared_axis[indextoletter[index]]["conv"]:
                            axis_conv = dic_shared_axis[indextoletter[index]]["conv"]
                        else:
                            axis_conv = "NO_COMPU_METHOD"
                    except:
                        axis_conv = "NO_COMPU_METHOD"
                    if axis_name:
                        sub_contents = self.set_content(
                            f"COM_AXIS NO_INPUT_QUANTITY {axis_conv} {c_instance.array_info[index]} {l_range}",
                            8,
                        )
                    else:
                        l_range = " ".join(self.a2l_type_info["type_range"]["uint32"])
                        sub_contents = self.set_content(
                        f"FIX_AXIS NO_INPUT_QUANTITY {axis_conv} {c_instance.array_info[index]} {l_range}",
                        8,
                    )
                    # if writable == "READ_ONLY":
                    #     sub_contents += self.set_content("READ_ONLY", 8)
                    if axis_name:
                        sub_contents += self.set_content(
                        f"AXIS_PTS_REF {axis_name}", 8
                        )
                    else:
                        # Fix_axis = "FIX_AXIS_PAR_DIST 0 {first} {second}"
                        # if index == 0:
                        sub_contents += self.set_content(f"FIX_AXIS_PAR_DIST 0 1 {c_instance.array_info[index]}",8)
                        # else:

                    # sub_contents += self.set_content("DEPOSIT ABSOLUTE", 8)
                    sub_contents += self.set_content(
                        f"EXTENDED_LIMITS {l_range}", 8
                    )
                    sub_contents += self.set_content('FORMAT "%.3"', 8)
                    contents += self.set_template_sub_item(
                        "AXIS_DESCR", sub_contents, 6
                    )
                else:
                    l_range = " ".join(self.a2l_type_info["type_range"]["uint32"])

                    sub_contents = self.set_content(
                        f"FIX_AXIS NO_INPUT_QUANTITY NO_COMPU_METHOD {c_instance.array_info[index]} {l_range}",
                        8,
                    )
                    # if writable == "READ_ONLY":
                    #     sub_contents += self.set_content("READ_ONLY", 8)
                    sub_contents += self.set_content(f"FIX_AXIS_PAR_DIST 0 1 {c_instance.array_info[index]}",8)
                    # sub_contents += self.set_content("DEPOSIT ABSOLUTE", 8)
                    sub_contents += self.set_content(
                        f"EXTENDED_LIMITS {l_range}", 8
                    )
                    sub_contents += self.set_content('FORMAT "%.3"', 8)
                    contents += self.set_template_sub_item(
                        "AXIS_DESCR", sub_contents, 6
                    )

        else:
            if len(c_instance.array_info) == 1: # 1차원 배열을 map으로보고싶으면 축하나 추가
                c_instance.array_info.append(1)
            array_info_reversed = c_instance.array_info[::-1]
                
            for dim_length in array_info_reversed:
                sub_contents = self.set_content(
                    f"FIX_AXIS NO_INPUT_QUANTITY NO_COMPU_METHOD  {dim_length} 0 0",
                    8,
                )
                sub_contents += self.set_content(
                    f"EXTENDED_LIMITS {var_range}",
                    8,
                )
                sub_contents += self.set_content("READ_ONLY", 8)
                sub_contents += self.set_content('FORMAT "%.3"', 8)
                sub_contents += self.set_content(
                    f"FIX_AXIS_PAR_DIST 0 1 {dim_length}", 8
                )
                contents += self.set_template_sub_item(
                    "AXIS_DESCR", sub_contents, 6
                )
        contents += self.set_link_map(
            display_range=var_range,
            symbol = symbol_name,
            var_addr=var_addr,
            var_addr_type=var_link_type,
        )
        contents += self.set_content('FORMAT "%.3"')
        measure_text = self.set_template_item(
            "CHARACTERISTIC", a2l_name, contents, comment=comment
        )
        self.A2L_str += measure_text
        return True
    
    def check_validity(self,a2l_name,a2l_type,symbol_name,c_instance):
        if a2l_type in ["MEASUREMENT","PARAMETER"]:
            if c_instance.IsStruct:
                self.warning_lst.append({"message":f"Cannot add {a2l_type} {a2l_name}, it is a struct!", "symbol":f"\"{symbol_name}\""})
                return False
            elif c_instance.IsArray:
                self.warning_lst.append({"message":f"Cannot add {a2l_type} {a2l_name}, it is an Array!", "symbol":f"\"{symbol_name}\""})
                return False
        elif a2l_type in ["MAP","STRING","AXIS"]:
            if c_instance.IsStruct:
                self.warning_lst.append({"message":f"Cannot add {a2l_type} {a2l_name}, it is a struct!", "symbol":f"\"{symbol_name}\""})
                return False
            elif not c_instance.array_info:
                self.warning_lst.append({"message":f"Cannot add {a2l_type} {a2l_name}, it is not an Array!", "symbol":f"\"{symbol_name}\""})
                return False
    
    def add_measure(self,\
                    var_addr,\
                    var_type, \
                    var_range, \
                    symbol_name,\
                    var_link_type,\
                    a2l_name,
                    c_instance = None,\
                    comment= "\"\"",\
                    compu_method = "NO_COMPU_METHOD",
                    bit_mask = None\
        ):
        if self.check_validity(a2l_name,"MEASUREMENT",symbol_name,c_instance) is False:
            return False
        contents = self.set_content(f"{var_type} {compu_method} 0 0 {var_range}")
        if bit_mask:
            contents += self.set_content(f"BIT_MASK {bit_mask}")

        contents += self.set_content(f"ECU_ADDRESS {var_addr}")
        contents += self.set_content("ECU_ADDRESS_EXTENSION 0x0")
        # contents += self.set_content('FORMAT "%.3"')
        # if not writable == "READ_ONLY":
        contents += self.set_content("READ_WRITE")
        contents += self.set_link_map(
            display_range=var_range,
            symbol = symbol_name,
            var_addr=var_addr,
            var_addr_type=var_link_type,
        )
        measure_text = self.set_template_item(
            "MEASUREMENT", a2l_name, contents, comment=comment
        )
        self.A2L_str += measure_text
        return True

    def add_parameter(self,\
                    var_addr,\
                    var_type, \
                    var_range, \
                    symbol_name,\
                    var_link_type,\
                    a2l_name,
                    c_instance = None,\
                    compu_method = "",\
                    comment = "\"\"",\
                    bit_mask = None \
        ):
        if self.check_validity(a2l_name,"PARAMETER",symbol_name,c_instance) is False:
            return False

        contents = self.set_content(
                f"VALUE {var_addr} __{var_type}_S 0 {compu_method} {var_range}"
            )
        if bit_mask:
            contents += self.set_content(f"BIT_MASK {bit_mask}")
        contents += self.set_content("ECU_ADDRESS_EXTENSION 0x0")
        contents += self.set_content(f"EXTENDED_LIMITS {var_range}")
        # contents += self.set_content('FORMAT "%.3"')
        contents += self.set_link_map(
            display_range=var_range,
            symbol = symbol_name,
            var_addr=var_addr,
            var_addr_type=var_link_type,
        )
        measure_text = self.set_template_item(
            "CHARACTERISTIC", a2l_name, contents, comment=comment
        )
        self.A2L_str += measure_text
        return True
    
    def get_symbol_info(self,symbol_name):
        try:
            c_instance = self.c_parser.symbol_shortcut[symbol_name]
            return c_instance
        except:
            # self.warning_lst.append(f"Cannot find symbol {symbol_name} in parsed data")
            on_other_variant = False
            for key, cparser in self.history.items():
                if symbol_name in cparser.symbol_shortcut:
                    on_other_variant =True
            if on_other_variant == False:
                if symbol_name in self.c_parser.not_copiled_symobol:
                    self.warning_lst.append({"message":f"Symbol is not compiled, No present in MAPXML", "symbol":f"\"{symbol_name}\""})
                else:                    
                    self.warning_lst.append({"message":f"Cannot find the symbol in parsed data", "symbol":f"\"{symbol_name}\""})
            
            return False
    
    def get_compu_and_common_axis(self,A2L_element,c_instance):
        compu_method = "NO_COMPU_METHOD"
        common_axis = {}
        symbol_name = A2L_element["SYMBOL_NAME"]
        # else: 
        if A2L_element["compu_method"]:
            compu_method = A2L_element["compu_method"]
        else:
            compu_method = "NO_COMPU_METHOD"
        if A2L_element["common_axis_x"] or A2L_element["conv_x"] :
            common_axis["x"] = {"name":A2L_element["common_axis_x"],\
                    "conv" : A2L_element["conv_x"]
                    }
        if A2L_element["common_axis_y"] or A2L_element["conv_y"]:
            common_axis["y"] = \
            {
                "name":A2L_element["common_axis_y"],\
                "conv" : A2L_element["conv_y"]
            }
        if c_instance.IsEnum:
            if c_instance.IsVecEnum:
                c_instance.type = "uint8"
            else:
                c_instance.type = "sint32"
            # if compu_method != "NO_COMPU_METHOD":
            #     self.warning_lst.append({"message":f"The variable is enum but you added another ConversionMethod", "symbol":f"\"{symbol_name}\""})
            compu_method = c_instance.name +".CONVERSION"
        return compu_method, common_axis
    
    def add_element(self,pathinfo,exl_info, validate_mode =False):
        if validate_mode:
            print("Checking every symbols address with t32")
            t32auto = T32_Auto(self.c_parser.symbol_shortcut,self.variant_name,pathinfo.project)
            t32auto.test_symbol()
            t32auto.disconnect()
        else:
            print(Fore.BLUE + f"[{self.actuator_name}] " + Fore.WHITE + f"Writing {self.variant_name}.a2l ...  ", end = "")
            for A2L_element in exl_info:
                if not A2L_element["SYMBOL_NAME"]:
                    continue
                symbol_name = A2L_element["SYMBOL_NAME"]
                a2l_type = A2L_element["A2LTYPE"]
                comment = f'"{self.actuator_name}"'
                # if A2L_element["COMMENT"]:
                #     comment = f'"{A2L_element["COMMENT"]}"'
                c_instance  = self.get_symbol_info(symbol_name)
                if not c_instance:
                    continue
                var_addr = c_instance.address
                bit_shift = 0
                bit_mask = c_instance.bitfield_mask
                a2l_name = A2L_element["A2L_Name"]
                compu_method, common_axis = self.get_compu_and_common_axis(A2L_element,c_instance)
                try :
                    var_link_type = self.a2l_type_info["type_what"][c_instance.type]
                except:
                    self.warning_lst.append({"message":f"Cannot add {symbol_name} as {a2l_type}","symbol":f"\"{symbol_name}\""})
                    self.warning_lst.append({"message":f"Symbol : {c_instance.name} as Type :{c_instance.type} is not supported", "symbol": f"\"{symbol_name}\"" } )
                    continue
                var_range = " ".join(self.a2l_type_info["type_range"][c_instance.type])
                var_type = self.a2l_type_info["type_asap"][c_instance.type]
                IsSuccessfullyAdded = False
                if A2L_element["A2LTYPE"].upper() == "PARAMETER":
                    IsSuccessfullyAdded = self.add_parameter(var_addr,\
                        var_type, \
                        var_range, \
                        symbol_name,\
                        var_link_type,\
                        a2l_name, \
                        c_instance=c_instance,\
                        compu_method = compu_method,\
                        bit_mask= bit_mask,\
                        comment = comment\
                    )
                elif A2L_element["A2LTYPE"].upper() == "MEASUREMENT":
                    IsSuccessfullyAdded = self.add_measure(var_addr,\
                        var_type, \
                        var_range, \
                        symbol_name,\
                        var_link_type,\
                        a2l_name ,\
                        c_instance=c_instance,\
                        compu_method = compu_method,\
                        bit_mask = bit_mask,\
                        comment = comment
                    )
                elif A2L_element["A2LTYPE"].upper() == "STRING":
                    IsSuccessfullyAdded = self.add_string(var_addr,\
                        var_type, \
                        var_range, \
                        symbol_name,\
                        var_link_type,\
                        a2l_name,
                        c_instance=c_instance,\
                        comment = comment


                    )
                elif A2L_element["A2LTYPE"].upper() == "AXIS":
                    IsSuccessfullyAdded = self.add_axis(var_addr,\
                        var_type, \
                        var_range, \
                        symbol_name,\
                        var_link_type,\
                        a2l_name,
                        compu_method=compu_method,\
                        c_instance = c_instance,\
                        comment = comment

                    )
                elif A2L_element["A2LTYPE"].upper() == "MAP":
                    IsSuccessfullyAdded = self.add_map(var_addr,\
                        var_type, \
                        var_range, \
                        symbol_name,\
                        var_link_type,\
                        a2l_name,\
                        compu_method = compu_method,\
                        dic_shared_axis = common_axis,\
                        c_instance = c_instance,\
                        comment = comment

                    )
                if IsSuccessfullyAdded:
                    self.added_a2l_elements[A2L_element["A2L_Name"]] = A2L_element
    
    def set_template_item(self,item, a2l_name, contents, comment='""', others="", indent=4):
        return (
            self.item.format(
                indent=" " * indent,
                ID=item,
                ID_NAME= a2l_name,
                comment=comment,
                others=others,
                contents=contents,
            )
            + "\n"
        )
    
    def set_content(self,text, indent=6):
        return "{s}{0}\n".format(text, s=" " * indent)

    def set_template_sub_item(self,item, contents, indent=4):
            return (
                self.sub_item.format(
                    indent=" " * indent, ID=item, contents=contents
                )
                + "\n"
            )

    def set_link_map(self,
            display_range,
            symbol,
            var_addr,
            var_addr_type,
            bit_shift="0",
            indent=6,
        ) -> str:
            return '{s}SYMBOL_LINK "{symbol}" 0\n{s}/begin IF_DATA CANAPE_EXT\n{s2}100\n{s2}LINK_MAP "{symbol}" {var_addr} 0x0 0 0x0 1 {var_addr_type} {bit_shift}\n{s2}DISPLAY 0x0 {display_range}\n{s}/end IF_DATA\n'.format(
                    # var_name=text,s
                    var_addr=var_addr,
                    var_addr_type=var_addr_type,
                    s=" " * indent,
                    s2=" " * (indent + 2),
                    bit_shift=bit_shift,
                    display_range= display_range,
                    symbol = symbol
            )
            
    
    def load_template(self):
        self.project_begin = asap_template.project_begin
        self.xcp = asap_template.XCP
        self.project_end = asap_template.project_end
        self.compu_linear = asap_template.compu_linear
        self.compu_tab_verb = asap_template.compu_tab_verb
        self.item = asap_template.item
        self.group_root = asap_template.group_root
        self.group = asap_template.group
        self.sub_group = asap_template.sub_group
        self.sub_item = asap_template.sub_item
        self.tab_element_format = asap_template.table_element
        self.tab_element_format_vtab = asap_template.table_element_vtab

    def set_A2L_basic_info(self,pathinfo):
        self.A2L_str = ""
        self.load_template()
        self.cro_dto_procotol = {
          
        }
        self.A2L_str += self.project_begin #add begining of a2l file
        self.A2L_str += self.xcp.format(cro=self.cro_dto_procotol[self.actuator_name]["cro"],\
             dto=self.cro_dto_procotol[self.actuator_name]["dto"]\
        ) #add xcp info
        par_file_path = pathinfo.project /"TuningParam"
        parfiles = par_file_path.glob("*.par")
        self.basic_vtab = {
            
        }
        for parfile in parfiles:
            tune_num = re.search(r"T(\d\d).+\.par", parfile.name).group(1)
        self.a2l_type_info = {\
            "type_asap": {\
                "boolean": "UBYTE",\
                "float32": "FLOAT32_IEEE",\
                "sint16": "SWORD",\
                "sint32": "SLONG",\
                "sint8": "SBYTE",\
                "uint16": "UWORD",\
                "uint32": "ULONG",\
                "uint8": "UBYTE"\
            },\
            "type_range": {\
                "boolean": [\
                    "0",\
                    "255"\
                ],\
                "float32": [\
                    "-3.40282346638529E+38",\
                    "3.40282346638529E+38"\
                ],\
                "sint16": [\
                    "-32768",\
                    "32767"\
                ],\
                "sint32": [\
                    "-2147483648",\
                    "2147483647"\
                ],\
                "sint8": [\
                    "-128",\
                    "127"\
                ],\
                "uint16": [\
                    "0",\
                    "65535"\
                ],\
                "uint32": [\
                    "0",\
                    "4294967295"\
                ],\
                "uint8": [\
                    "0",\
                    "255"\
                ]\
            },
            "type_size": {
                "boolean": "8",
                "float32": "32",
                "sint16": "16",
                "sint32": "32",
                "sint8": "8",
                "uint16": "16",
                "uint32": "32",
                "uint8": "8"
            },
            "type_what": {
                "boolean": "0x87",
                "float32": "0x1",
                "sint16": "0xCF",
                "sint32": "0xDF",
                "sint8": "0xC7",
                "uint16": "0x8F",
                "uint32": "0x9F",
                "uint8": "0x87"
            },
            
        }
        self.compu_method_infos = {\
           
            
        }
        
    def write_text(self,Path, text, encoding=None,printing_result = True) -> bool:
        """write text
        :param Path Path: Path to write
        :param str text: text to write
        :returns: True if writed, False for not changed.
        """
        changed = ""
        if Path.exists():
            try:
                if Path.read_text(encoding=encoding) == text:
                    if printing_result:
                        print(Fore.GREEN + "Done(nothing's changed)")
                    return False
            except:
                if Path.read_text(encoding="ISO-8859-1") == text:
                    return False

        # write if path not exist or text differs
        try:
            Path.write_text(text, encoding=encoding)
        except:
            Path.write_text(text, encoding="ISO-8859-1")
        if printing_result:
            print(Fore.GREEN + "Done")
        return True
