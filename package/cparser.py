from collections import deque
from copyreg import pickle
from pathlib import Path
import re
from package.mapxml import MapXml
from package import filetool
from .c_struct import C_struct
from library.colorama import init, Fore, Back, Style
from .preprocess import preprocessor_2
import pickle
import subprocess
import json

class Cparser:
    def __init__(self,target_project,pathinfo) -> None:
        self.target_project = target_project
        self.pathinfo = pathinfo
        self.not_copiled_symobol = {}
        self.file_date = []
        
        self.src = {}
        list.index
        self.set_internal_variables()
        self.read_source()
        

    def set_internal_variables(self):
        self.defines = {}
        self.defines["FALSE"] = '0'
        self.defines["TRUE"] = '1'
        self.defines["STD_ON"] = '1'
        self.defines["STD_OFF"] = '0'
        self.defines["USE_BOOT"] = '1'
        self.symbol_shortcut = {}
        self.address = {}
        self.address_infos = {}
        self.singletypedef = {}
        self.singletypedef["Std_ReturnType"] = "uint8"
        self.weird_defines = {} #defines have sizeof as value
        self.regex = {}
        self.vector_enum = {}
        self.typedef_struct_ref = {}
        self.regex["single line static"] = r"(\w+)\s+([^\s^;]+)"
        self.all_statics = []
        self.src_need_preprocess = {}
        self.platform_type ={ \
            "uint8":1, "sint8":1,"uint16":2, "sint16":2,"uint32":4, \
                "sint32":4,"float32":4,"boolean":1, "char":1 ,"int":4\
        }
        self.static_typ_decl_pair = {"platform_type": {}, "typedef_type" : {}}
        self.statics = {}
        self.defines_for_preprocess = {"FALSE" : "0", "TRUE":"1","USE_BOOT" :"1"}
        self.platform_type_static_ref = {}
        self.codesToPreprocess = ""
        init(autoreset=True)

    def search_instance(self,A2L_element):
        if "." in A2L_element["SYMBOL_NAME"]:
            var_name = A2L_element["SYMBOL_NAME"].split(".")[0]
            return self.initialized_typedef[var_name]["instance"].search_element(A2L_element["SYMBOL_NAME"])
        else:
            var_name = A2L_element["SYMBOL_NAME"]
            return self.initialized_typedef[var_name]
        
    def parse_vector_enum(self,src):
        # result = re.findall(r"""[ ]\*[ ](\w+)\:[ ]Enumeration.+\n([\s\S]*?)(?=\)\n[ ]\*[ ]\w)""",src)
        result = re.findall(r"""(?<=[ ]\*[ ])(\w+):.+\n([\w(\s\*)]+)\)""",src)
        for vec_enum in result:
            vec_enum_name = vec_enum[0]
            vect_enum_element = vec_enum[1]
            vect_enum_element = vect_enum_element.split(" *   ")
            vec_enum_instance = C_struct(vec_enum_name,"",instance_type="enum")
            vec_enum_instance.IsVecEnum = True
            vec_enum_instance.type_size = 1
            for element in vect_enum_element:
                line_search = re.search(r"(\w+)\s+\((\d+)[uU]*",element)
                if line_search:
                    enum_element = C_struct("",line_search.group(1))
                    enum_element.enum_val = int(line_search.group(2))
                    vec_enum_instance.elements.append(enum_element)
            self.vector_enum[vec_enum_name] = {"instance" :vec_enum_instance}

    def gather_var(self,typ,decl):
        new_c_struct = C_struct(typ, decl)
        # typ = new_c_struct.type
        name = new_c_struct.name
        self.statics[name] = new_c_struct

    def remove_comment(self,src):
        src = re.sub(r"//.+","",src)
        self.parse_vector_enum(src)
        src = re.sub(r"/\*[\s\S]*?\*/","",src)
        src = re.sub(r"unsigned\s+char","uint8",src)
        src = re.sub(r"unsigned\s+int","uint32",src)
        src = re.sub(r"\s+char\s+"," sint8 ",src)
        src = re.sub(r"\s+int\s+"," sint32 ",src)
        src = re.sub(r"(?<=\n)\#if\s+0.*\s+[\w\s{:;}=,\[\]]+\#endif","",src)
        src = re.sub(r"\\\n", "", src)
        return src

    def read_ecu_type(self,mapxml):
        sysopt = self.pathinfo.project / "Appl/Source/hclibrary/SystemOption.h"
        try:
            sysopt_open = open(sysopt.absolute().as_posix(),"r",encoding = "utf-8")
            src  = sysopt_open.read()
        except:
            sysopt_open = open(sysopt.absolute().as_posix(),"r",encoding = "ISO-8859-1")
            src  = sysopt_open.read()
        _, src,_ = preprocessor_2(src,self.defines_for_preprocess)
        try:
            vscodetask_open = open(self.pathinfo.vscodetask.absolute().as_posix(),"r",encoding = "utf-8")
            taskjson = json.load(vscodetask_open)
        except:
            vscodetask_open = open(self.pathinfo.vscodetask.absolute().as_posix(),"r",encoding = "ISO-8859-1")
            taskjson = json.load(vscodetask_open)
        spec_name = taskjson["tasks"][1]["label"].split("[")[1].split("]")[0].strip()
        actuator_name = "RWA_M"
        for result in re.findall(r"(\w\w\w_\w).mapxml",mapxml.name):
            actuator_name = result
            
        spec_json_file = self.pathinfo.speclist / f"{spec_name}.json"
        try:
            spec_json_file_open = open(spec_json_file.absolute().as_posix(),encoding = "utf-8")
            self.defines_for_preprocess.update(json.load(spec_json_file_open)[actuator_name])
        except:
            spec_json_file_open = open(spec_json_file.absolute().as_posix(),encoding = "ISO-8859-1")
            self.defines_for_preprocess.update(json.load(spec_json_file_open)[actuator_name])
    
    def check_blackbox_enums(self,src):
        regex_for_blackbox = re.compile(r"""\s*typedef[ ]\b(struct|enum|union)
                ((?:(?!typedef )[\s\S])*)}[ ]*
                \b(\w+);\n
                \/\*[ ]\<end\>[ ](\w+)\,.+\n""", re.VERBOSE)

    

    def read_source(self):
        if not self.src:
            print("Reading Sources ... ", end ="")
            for c_file in self.c_files:
                try:
                    f = open(c_file.as_posix(),"r",encoding = "utf-8")
                    src  = f.read()
                except:
                    f = open(c_file.as_posix(),"r",encoding = "ISO-8859-1")
                    src = f.read()
                # if c_file.stem != "PublicLibrary":
                self.check_blackbox_enums(src)
                src = self.remove_comment(src)
                self.src[c_file.name] = src
            print(Fore.GREEN + "Done")
            
    
    def make_references(self):
        self.build_references(self.src)

    def build_references(self, src_dict,preprocess = False):
        for c_file_name, src in src_dict.items():
            # if preprocess:
            # self.build_define_ref(src.split("\n"),c_file_name,src)
            strNeedsPreprocessing = ""
            _, src ,strNeedsPreprocessing = preprocessor_2(src,self.defines_for_preprocess, save_defines = True, suppress_error=True)
            self.codesToPreprocess += "".join(strNeedsPreprocessing)
            # self.build_typedef_struct_ref(src,self.typedef_struct_ref,c_file_name)   
            # self.build_other_ref(src.split("\n"),c_file_name,src)
        _, src ,_ = preprocessor_2(src,self.defines_for_preprocess, save_defines = True, suppress_error=False)
        
        for c_file_name, src in src_dict.items():
            _, src,_ = preprocessor_2(src,self.defines_for_preprocess, save_defines = False)
            self.build_typedef_struct_ref(src,self.typedef_struct_ref,c_file_name)   
            self.build_other_ref(src.split("\n"),c_file_name,src)

    def run_setting_change(self,mapxml):
        args_ecu_type = "_".join(mapxml.stem.split("_")[-2:])
        print(Fore.BLUE + f"[{args_ecu_type}] " + Fore.WHITE + f"Changing ECU_Type.h to {args_ecu_type} ... ",end = "")
        cmd = f"python Submodule\\TOOLS.SIMPL\\_simpl.py change_vscodetaskjson --cursysopt {args_ecu_type}"
        process = subprocess.call(
            cmd,
            shell=True,
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        print(Fore.GREEN + "Done")
    
    def parse_global_variables(self,src):
        regex_global_rte = r"^VAR\((.+),.+\)\s+(\w+)"
        regex_global = r"^(?!static|inline|typedef|void)(\w+)\s+([\w\[\]]+)"
        result = re.findall(regex_global_rte,src,re.M)
        for global_rte in result:
            typ = global_rte[0]
            decl = global_rte[1]
            self.gather_var(typ,decl)

        result = re.findall(regex_global,src,re.M)
        for global_var in result:
            typ = global_var[0]
            decl = global_var[1]
            self.gather_var(typ,decl)
    
    def build_typedef_struct_ref(self,src,typedef_struct_ref,file_name):
        typedef_struct_regex = re.compile(r"""\btypedef[^{;]+;
        |
        \btypedef[ ]\b(struct|enum|union)
        ((?:(?!typedef )[\s\S])*)}[ ]*
        \b(\w+);""",re.VERBOSE)

        #new regex for typedefs
        typedef_struct_regex = re.compile(r"""(?<=typedef[ ])(struct|enum|union)\s*\{
            ((?:[\s\S](?!typedef))+)\}\s{0,2}(\w+)\;""",re.VERBOSE)
        typedef_struct_regex = re.compile(r"""(?<=typedef[ ])(struct|enum|union)\s*(?:[\w]+)?\s+\{
            ((?:[\s\S](?!typedef))+)\}\s{0,2}(\w+)\;""",re.VERBOSE)
        just_struct_regex = re.compile(r"""^(struct|enum|union)\s+(\w+)\s+\{
            ([\s\S]+)\}\s*;""")
        self.parse_global_variables(src)

    

        for regex in typedef_struct_regex.findall(src):
            if "" in regex:
                continue
            instance_type = regex[0]
            src = regex[1]
            typ_name = regex[2]
            new_struct = C_struct(typ_name,"",instance_type=instance_type,src =src.split("\n"))
            if typ_name not in typedef_struct_ref:
                typedef_struct_ref[typ_name] = {"file_name" : file_name,"instance": new_struct}
            self.process_inside_typedef(new_struct,file_name)

        for regex in just_struct_regex.findall(src):
            if "" in regex:
                continue
            instance_type = regex[0]
            src = regex[2]
            typ_name = regex[1] + "%tmptype"
            decl = regex[1]
            self.gather_var(type_name, decl)
            new_struct = C_struct(typ_name,"",instance_type=instance_type,src =src.split("\n"))
            if typ_name not in typedef_struct_ref:
                typedef_struct_ref[typ_name] = {"file_name" : file_name,"instance": new_struct}
            self.process_inside_typedef(new_struct,file_name)
    
    def process_inside_typedef(self,input_c_struct,file_name): #유니온 안에 새로운 스트럭트 선언, 유니온 안에 이넘 등등 안됨 일중 유니온, 이넘 만됨
        queue = []
        struct_src = []
        enum_default_numbering = 0        
        for line in input_c_struct.src:
            line = line.lstrip()
            if line.startswith("struct") or line.startswith("enum"):
                if len(queue) != 0:
                    struct_src.append(line)
                queue.append(line)
            elif line.startswith("}"):
                found_type = ""
                if "struct"in queue[-1] or "enum"in queue[-1]:
                    if "struct" in queue[-1]:
                        found_type ="struct"
                    elif "enum" in queue[-1]:
                        found_type = 'enum'
                    # print(found_type)
                    queue.pop(-1)
                if len(queue) == 0 and ";" in line:
                    if line.split("}")[1]:
                        new_c_struct = C_struct("", line.split("}")[1].split(";")[0].strip(),instance_type=found_type, src= struct_src)
                        input_c_struct.add_struct_element(\
                            new_c_struct\
                        )
                        self.process_inside_typedef(new_c_struct,file_name)
                    struct_src = []
                elif len(queue) == 0 and ";" not in line:
                    for_error = "\n".join(input_c_struct.src)
                    raise Exception (f" {file_name}  : please check if struct name and closure are in the same line{for_error} ")
                else:
                    struct_src.append(line)

            elif len(queue) > 0:
                struct_src.append( line)

            elif len(queue) == 0: 
                if line == line.strip and ";" in line:
                    new_c_struct = C_struct("", line.split("}")[1].split(";")[0].strip(),instance_type="struct", src= struct_src)
                    input_c_struct.add_struct_element(\
                        new_c_struct\
                    )
                    self.process_inside_typedef(new_c_struct,file_name)
                    struct_src = []
                    
                if input_c_struct.IsEnum:
                    enum_element_regex = re.compile("\s*(\w+)\s+\=\s+(\d+)")
                    if enum_element_regex.search(line):
                        enum_element_name = enum_element_regex.search(line).group(1)
                        enum_element_val = enum_element_regex.search(line).group(2)

                        new_c_struct = C_struct("", enum_element_name)
                        self.defines[enum_element_name]= enum_element_val
                        new_c_struct.enum_val = enum_element_val
                        input_c_struct.add_struct_element(\
                            new_c_struct
                        )
                        input_c_struct.type_size = 4
                    elif re.search(r"\s*(\w+)\s*",line):
                        enum_element_name = re.search(r"\s*(\w+)\s*",line).group(1)
                        new_c_struct = C_struct("", enum_element_name)
                        self.defines[enum_element_name]= str(enum_default_numbering)
                        new_c_struct.enum_val = enum_default_numbering
                        input_c_struct.add_struct_element(\
                            new_c_struct
                        )
                        input_c_struct.type_size = 4
                        enum_default_numbering += 1

                else:
                    single = re.compile("\s*(\w+)\s+([^;]+)")
                    if single.search(line):
                        if single.search(line).group(1) in self.typedef_struct_ref:
                            if self.typedef_struct_ref[single.search(line).group(1)]["instance"].IsEnum:
                                new_c_struct = C_struct(single.search(line).group(1), single.search(line).group(2),instance_type="enum")
                            elif self.typedef_struct_ref[single.search(line).group(1)]["instance"].IsUnion:
                                new_c_struct = C_struct(single.search(line).group(1), single.search(line).group(2),instance_type="union")
                            else:
                                new_c_struct = C_struct(single.search(line).group(1), single.search(line).group(2),instance_type="struct")
                        else:
                            new_c_struct = C_struct(single.search(line).group(1), single.search(line).group(2))
                        input_c_struct.add_struct_element(\
                            new_c_struct
                    )

    def build_other_ref(self,lines,file_name,src,preprocess = False):
        regex_static = r"(?<=static)\s+(?:volatile|const)?\s*(\w+)\s+([\w\[\]\s\-\+\/\%]+)"
        regex_const = r"^const\s+(?:volatile|const)?\s*(\w+)*\s+([\w\[\]]+)"
        regex_single_typedef = r"typedef\s+(\w+)\s+([^;]+)"
        regex_func_pointer = r"\(\*(\w+)\)\("
    
        for line in lines:
            if line.strip().startswith("static") or line.strip().startswith("volatile"):
                # for result in result_const:
                    result_static = re.search(regex_static,line)
                    if result_static:
                        typ = result_static.group(1).strip()
                        decl = result_static.group(2).strip()
                        self.gather_var(typ,decl)

            elif line.strip().startswith("const"):
                    result_const = re.search(regex_const,line)
                    if result_const:
                        typ = result_const.group(1)
                        decl = result_const.group(2)
                        self.gather_var(typ,decl)
                    
            elif line.startswith("typedef"):
                if "struct" in line.split("typedef")[1] or "enum" in line.split("typedef")[1]: # typdef struct
                    typedef_struct_found = True
                else:# single typedef
                    tmp_re = re.compile(regex_single_typedef)
                    if tmp_re.search(line):
                        tmp_fp = re.compile(regex_func_pointer)
                        if tmp_fp.search(tmp_re.search(line).group(2)):
                            self.singletypedef[tmp_fp.search(line).group(1)] = 'uint32'
                        else:
                            self.singletypedef[tmp_re.search(line).group(2)] = tmp_re.search(line).group(1)

            elif line.startswith("#define"): #for #define
                if line.startswith("define"):
                    line = line.split("define")[1]
                    # tmp_re = re.compile(r"\s+(\w+)\s+\(*([\"\w\d.]+)\)*") 
                    tmp_re = re.compile(r"\s+(\S+)\s+(.+)") 
                    if tmp_re.search(line):
                        self.defines[tmp_re.search(line).group(1)] = tmp_re.search(line).group(2)
    
    def build_define_ref(self,lines,file_name,src,preprocess = False):
        for line in lines:
            if line.startswith("#define"): #for #define
                if line.startswith("define"):
                    line = line.split("define")[1]
                    # tmp_re = re.compile(r"\s+(\w+)\s+\(*([\"\w\d.]+)\)*") 
                    tmp_re = re.compile(r"\s+(\S+)\s+(.+)") 
                    if tmp_re.search(line):
                        self.defines[tmp_re.search(line).group(1)] = tmp_re.search(line).group(2)
                        self.defines_for_preprocess[tmp_re.search(line).group(1)] = tmp_re.search(line).group(2)

    def write_symbol_shortcut(self):
        file_path = Path(Path(__file__).parent) / "symbol_shortcut.json"
    
    def write_change_date(self):
        date_file_path = Path(Path(__file__).parent) / "file_date.json"
        filetool.write_json(date_file_path,self.file_date)

    def check_change_date(self,c_files):
        date_file_path = Path(Path(__file__).parent) / "file_date.json"
        only_chaned_files = []
        try:
            try:
                self.file_date = filetool.read_jsonc(date_file_path)
            except:
                self.file_date = {}
            for c_file in self.c_files:
                if c_file.name in self.file_date:
                    if c_file.stat().st_ctime == self.file_date[c_file.name]:
                        continue
                
                self.file_date[c_file.name] = (c_file.stat().st_ctime)
                only_chaned_files.append(c_file)
        except:
            return
        else:
            self.c_files = only_chaned_files
    
    def search_symbol_by_type(self,input_type):
        for symbol in self.symbol_shortcut:
            if self.symbol_shortcut[symbol].type == input_type:
                return self.symbol_shortcut[symbol]

    def process_remained_define(self):
        for symbol in self.symbol_shortcut:
            if self.symbol_shortcut[symbol].remained_defines:
                regex_sizeof = r"(sizeof\(?([\w.]+)\)?)"
                calculated_index = []
                for remained_define in self.symbol_shortcut[symbol].remained_defines:
                    symbol = self.symbol_shortcut[symbol]
                    if remained_define.startswith("("):
                        remained_define = remained_define.strip("(")
                        remained_define = remained_define[0:len(remained_define)-1]
                    result = re.findall(regex_sizeof,remained_define)
                    replace = []
                    for sizeof_term in result:
                        term_str = sizeof_term[0]
                        term_val = sizeof_term[1]
                        replace.append({"term_str":"","size":""})
                        replace[-1]["term_str"] = term_str
                        if term_val in self.platform_type:
                            replace[-1]["size"] = str(self.platform_type[sizeof_term])
                        elif term_val in self.typedef_struct_ref:
                            c_instance = self.search_symbol_by_type(term_val)
                            replace[-1]["size"] = str(c_instance.size)
                        elif term_val in self.symbol_shortcut:
                            replace[-1]["size"] = str(self.symbol_shortcut[term_val].size)
                    for sizeof_term in replace:
                        remained_define = remained_define.replace(sizeof_term["term_str"],sizeof_term["size"])
                    calculated_index.append(int(eval(remained_define)))
                index = 0
                symbol.num_of_array = 1
                for _ in symbol.array_info:
                    symbol.array_info[index] = calculated_index[index]
                    symbol.num_of_array *= calculated_index[index]
                    index+= 1
                symbol.size = symbol.type_size*symbol.num_of_array
                
    def process_source(self,mapxml):
        args_ecu_type = "_".join(mapxml.stem.split("_")[-2:])
        self.update_struct_members(args_ecu_type)
        self.replace_typedef(args_ecu_type)
        self.process_defines()
        self.replace_index_defines(args_ecu_type)
        self.update_struct_size(args_ecu_type)
    
    def process_with_map(self, mapxml):
        args_ecu_type = "_".join(mapxml.stem.split("_")[-2:])
        print(Fore.BLUE+ f"[{args_ecu_type}] " + Fore.WHITE + f"Processing with {mapxml.name} ...  ", end ="")
        self.read_addr_info_from_xml(mapxml)
        self.process_remained_define()
        self.link_static_with_typedef()
        print(Fore.GREEN + "Done")
        break_here = {}
    
    def update_struct_members(self,actuator_name):
        print(Fore.BLUE + f"[{actuator_name}] " + Fore.WHITE+ "Updating all members of structures  ...  ",end="")
        for typedef in self.typedef_struct_ref:
            self.typedef_struct_ref[typedef]["instance"].update_elements(self.typedef_struct_ref)
        print(Fore.GREEN + "Done")
    
    def replace_typedef(self,actuator_name):
        print(Fore.BLUE + f"[{actuator_name}] " + Fore.WHITE+ "Replacing type defined ...  ", end ="")
        for typedef in self.typedef_struct_ref:
            self.typedef_struct_ref[typedef]["instance"].replace_type(self.singletypedef,self.typedef_struct_ref,self.vector_enum)
        print(Fore.GREEN + "Done")
    
    def replace_index_defines(self,actuator_name):
        print(Fore.BLUE + f"[{actuator_name}] " + Fore.WHITE+ "Processing array index ...  ", end ="")
        for typedef in self.typedef_struct_ref:
            self.typedef_struct_ref[typedef]["instance"].replace_defines_in_braces(self.defines)
        print(Fore.GREEN + "Done")
    
    def update_struct_size(self,actuator_name):
        print(Fore.BLUE + f"[{actuator_name}] " + Fore.WHITE+ "Processing struct sizes ...  ", end ="")
        for typedef in self.typedef_struct_ref:
            self.typedef_struct_ref[typedef]["instance"].update_elements_size()
        print(Fore.GREEN + "Done")
    
    def find_end_of_definition(self, input_define):
        if input_define in self.defines:
            return self.find_end_of_definition(self.defines[input_define])
        else:
            return input_define
    
    def process_defines(self):
        double_defines = {}
        for define in self.defines:
            regex_float = r"\(*([\d\.]+)[Ff]\)"
            regex_int = r"\(*([\d]+)[Uu]*\)*"
            regex_hex = r"\(*(0x[0-9a-fA-F]+)[Uu]*\)*"
            regex_weird_define= r"[\.\/\+\*\-\?\<\:]|sizeof"
            if '"' in self.defines[define]: #스트링이면
                self.defines[define] = self.defines[define].strip('"')
            elif re.search(regex_float,self.defines[define]): #플롯이면
                result = re.search(regex_float,self.defines[define]).group(1)
                self.defines[define] = result
            elif re.search(regex_hex,self.defines[define]): #헥사면
                result = re.search(regex_hex,self.defines[define]).group(1)
                self.defines[define] = result
            elif re.search(regex_int,self.defines[define]): #인트면
                result = re.search(regex_int,self.defines[define]).group(1)
                self.defines[define] = result
            elif re.search(regex_weird_define,self.defines[define]):  #수식이있으면
                self.weird_defines[define] = self.defines[define]
            else: #다시 디파인이면
                double_defines[define] = self.defines[define]
            
        for define in double_defines:
            if double_defines[define].startswith("("):
                double_defines[define] =double_defines[define][1:len(double_defines[define])-1]
            result = self.find_end_of_definition(double_defines[define])
            if result:
                double_defines[define] = result
        self.defines.update(double_defines)
    
    def link_platform_type(self):
        for name in self.platform_type_static_ref:
            if name in self.address_infos:
                self.platform_type_static_ref[name]["instance"].replace_type(self.singletypedef,self.typedef_struct_ref,self.vector_enum)
                self.platform_type_static_ref[name]["instance"].replace_defines_in_braces(self.defines)
                self.platform_type_static_ref[name]["instance"].update_address(int(self.address_infos[name],16))
                if self.platform_type_static_ref[name]["instance"].IsArray:
                    duplecated_instances = self.platform_type_static_ref[name]["instance"].process_array()
                    for instance in duplecated_instances:
                        instance.update_symbol_hierachy(self)
                else:
                    self.platform_type_static_ref[name]["instance"].duplicate_array_element()
                self.platform_type_static_ref[name]["instance"].update_symbol_hierachy(self)

    # def store_blackbox_symbol(self,c_instance):
        # self.black
    def link_typedef_type(self):
        
        for name in self.statics:
            if name in self.address_infos:
                self.statics[name].replace_type(self.singletypedef,self.typedef_struct_ref,self.vector_enum)
                typ = self.statics[name].type
                if typ in self.typedef_struct_ref:
                    copied_instance = pickle.loads(pickle.dumps(self.typedef_struct_ref[typ]["instance"]))
                    copied_instance.name = name
                   
                    if self.statics[name].IsArray:
                        copied_instance.array_info = self.statics[name].array_info
                        copied_instance.IsArray = True

                    copied_instance.replace_defines_in_braces(self.defines)
                    copied_instance.update_address(int(self.address_infos[name],16))
                    copied_instance.update_symbol_hierachy(self)
                    if copied_instance.IsArray:
                        duplecated_instances = copied_instance.process_array()
                        for instance in duplecated_instances:
                            instance.update_symbol_hierachy(self)
                    else:
                        copied_instance.duplicate_array_element()
                    copied_instance.update_symbol_hierachy(self)
                elif typ in self.vector_enum:
                    copied_instance = pickle.loads(pickle.dumps(self.vector_enum[typ]["instance"]))
                    copied_instance.name = name
                    if self.statics[name].IsArray:
                        copied_instance.array_info = self.statics[name].array_info
                        copied_instance.IsArray = True
                    copied_instance.replace_defines_in_braces(self.defines)
                    copied_instance.update_address(int(self.address_infos[name],16))
                    copied_instance.update_symbol_hierachy(self)
                    if copied_instance.IsArray:
                        duplecated_instances = copied_instance.process_array()
                        for instance in duplecated_instances:
                            instance.update_symbol_hierachy(self)
                    else:
                        copied_instance.duplicate_array_element()
                    copied_instance.update_symbol_hierachy(self)
                elif typ in self.singletypedef:
                    c_instance = C_struct(self.singletypedef[typ],name)
                    c_instance.replace_defines_in_braces(self.defines)
                    c_instance.update_address(int(self.address_infos[name],16))
                    c_instance.update_symbol_hierachy(self)
                    if c_instance.IsArray:
                        duplecated_instances = copied_instance.process_array()
                        for instance in duplecated_instances:
                            instance.update_symbol_hierachy(self)
                    else:
                        c_instance.duplicate_array_element()
                    c_instance.update_symbol_hierachy(self)
                elif typ in self.platform_type:
                    c_instance = self.statics[name]
                    c_instance.replace_defines_in_braces(self.defines)
                    c_instance.update_address(int(self.address_infos[name],16))
                    # if self.statics[name].IsArray:
                    #     c_instance.array_info = self.statics[name].array_info
                    #     c_instance.IsArray = True
                    c_instance.process_size_of(self)
                    c_instance.update_symbol_hierachy(self)
                    if c_instance.IsArray:
                        duplecated_instances = c_instance.process_array()
                        for instance in duplecated_instances:
                            instance.update_symbol_hierachy(self)
                    else:
                        c_instance.duplicate_array_element()
                    c_instance.update_symbol_hierachy(self)
            else:
                self.not_copiled_symobol[name] = 1
                

           
    def link_static_with_typedef(self):
        self.link_typedef_type()
        self.link_platform_type()

    def read_addr_info_from_xml(self, mapxml_path):
        mapfile = mapxml_path
        mapxml = MapXml(mapfile)
        mapxml.arrange_data()
        self.address_infos = mapxml.addr_info

    def search_node(self,input_str,input_dict):
        ret = None
        if input_str not in input_dict:
            if type(input_dict) != dict:
                return None
            for node in input_dict:
               if self.search_node(input_str,input_dict[node]):
                   ret = self.search_node(input_str,input_dict[node])
        else:
            ret = input_dict
        return ret
    
    def add_node(self,parnet_node, input_dict, child_node,input_c_struct = {}):
        # add node to given parnet_node
        ret = None
        if parnet_node not in input_dict:
            for node in input_dict:
                if type(input_dict[node]) == dict:
                    ret =  self.add_node(parnet_node,input_dict[node],child_node,input_c_struct)
               
        else:
            input_dict[parnet_node][child_node] = input_c_struct
            ret = True     
        return ret
    
