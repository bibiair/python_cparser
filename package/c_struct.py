from collections import deque
from pathlib import Path
import re 
import pickle
class C_struct:
    def __init__(\
                self,\
                c_type,\
                name,\
                num_of_array = 1,\
                array_info = None,\
                instance_type = False,\
                src = None,\
                init_val =None,
                struct_elements = [] ,\
                preprocessed = False,\
                contains_preprocessed = False\
        ):
        self.preprocessed = preprocessed
        self.contains_preprocessed = contains_preprocessed
        self.recursion_depth = 50
        self.address = 0
        self.bitfield = 0 
        self.biggest_element_size = 0
        self.array_info = []
        if array_info:
            self.array_info = array_info
        self.num_of_array = num_of_array
        self.symbol_hierachy = ""
        self.padded = False
        self.IsSingle = True
        self.remained_defines = []
        self.HasBitfield =False
        self.bitfield_mask = 0
        self.IsStruct = False
        self.IsArray = False
        self.IsEnum = False
        self.IsPointer = False
        self.IsUnion = False
        self.IsVecEnum = False
        self.platform_type ={ \
            "uint8":1, "sint8":1,"uint16":2, "sint16":2,"uint32":4, \
                "sint32":4,"float32":4,"boolean":1,"char":1,"int":1\
        }
        self.name = name
        self.elements = []
        self.elements += struct_elements
        self.src = src
        self.enum_val = None

        if instance_type == "enum":
            self.IsEnum = True

        if instance_type == "union":
            self.IsUnion = True
            self.IsSingle = False
        if len(struct_elements) >= 1 or instance_type == "struct":
            self.IsStruct = True
        if "[" in self.name:
            tmp = self.name.split("[")
            self.name = tmp [0]
            tmp = tmp[1:]
            self.IsArray = True
            for index_str in tmp:
                self.array_info.append(index_str.split("]")[0])
        
        if self.num_of_array >= 2:
            self.IsArray = True
        if self.IsStruct or self.IsEnum:
            self.IsSingle = False
        self.bitfield_info = []
        if self.IsSingle:
            if ":" in self.name:
                self.bitfield = int(name.split(":")[-1])
                self.name = self.name.split(":")[0].strip()
        self.type = c_type
        self.size = 0   #size for entire size considering num_of_array
        self.type_size = 0 #type_size means size of type ex)platform-types(uint8...), structure, eunu
        if self.type in self.platform_type:
            self.type_size = self.platform_type[self.type]
            self.size = self.platform_type[self.type]
        if "*" in self.name : 
            # self.size = 4
            self.IsStruct = False
            self.IsPointer = True
            self.IsSingle = True
            self.type_size = self.platform_type["uint32"]
            
    def process_size_of(self,cparser):
        if self.remained_defines:
            regex_sizeof = r"(sizeof\(?([\w.]+)\)?)"
            calculated_index = []
            for remained_define in self.remained_defines:
                symbol = self
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
                    if term_val in cparser.platform_type:
                        replace[-1]["size"] = str(cparser.platform_type[sizeof_term])
                    elif term_val in cparser.typedef_struct_ref:
                        c_instance = cparser.search_symbol_by_type(term_val)
                        replace[-1]["size"] = str(c_instance.size)
                    elif term_val in cparser.symbol_shortcut:
                        replace[-1]["size"] = str(cparser.symbol_shortcut[term_val].size)
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
    def update_address(self, symbol_address):
            if self.IsStruct or self.IsUnion:
                    buff = []
                    self.address = hex(symbol_address)
                    for element in self.elements:
                        # if element.name != "#padding":
                        if self.IsStruct:
                            address_from_offset = (symbol_address + element.address)
                        else:
                            address_from_offset = (symbol_address)
                        element.address = hex(address_from_offset)
                        element.update_address(address_from_offset)
                        buff.append(element)
                    buff = self.elements
            else:
                self.address = hex(symbol_address)

    def process_array(self):
        if self.IsArray:
            ret = []
            offset = 0
            duplicated_self_list = self.duplicate_self_array()
            for duplicated_self in duplicated_self_list:
                # duplicated_self.update_address(int(self.address,base=16)+self.type_size*offset)
                duplicated_self.duplicate_array_element()
                offset += 1
                ret.append(duplicated_self)
            return ret

    def search_type_in_ref(self, input,single_def_ref,typdef_sturct_ref):
        for_exception = input
        ret = None
        if input in single_def_ref or input in self.platform_type:
            index = 0
            while input not in self.platform_type:
                if index > self.recursion_depth:
                    raise Exception (f"cannot find recursely for type {for_exception} ")

                index += 1
                input = single_def_ref[input]
            ret = input
        elif input in typdef_sturct_ref:
            ret = pickle.loads(pickle.dumps(typdef_sturct_ref[input]["instance"]))
        return ret

    def replace_defines_in_braces(self,single_defines_reference):
        if self.IsArray and len(self.array_info) > 0:
            index = 0
            for index_str in self.array_info: #배열안의 디파인이 만약에 이중으로 디파인되어있으면 여기 수정해야됨, 지금은 일단 이중 파싱 없다고 가정
                if type(index_str) != int:
                    for_math = re.split("[\-\+\\\*]",index_str)
                    if index_str in single_defines_reference:  #배열 선언 인덱스가 디파인 값이면
                        try:
                            self.array_info[index] = int(single_defines_reference[index_str])
                        except:
                            self.remained_defines.append(single_defines_reference[index_str])
                    elif len(for_math) > 1: #수식이면
                        for value in for_math:
                            value = value.strip()
                            if value in single_defines_reference:
                                index_str = re.sub(value,single_defines_reference[value], index_str)
                                    
                        self.array_info[index] = eval(index_str)
                    else:
                        index_str = re.search(r"(\d+)[uU]*",index_str).group(1)
                        self.array_info[index] = int(index_str)
                index = 1
            self.num_of_array = 1
            for to_mult_all_index in self.array_info:
                self.num_of_array *= to_mult_all_index
        for element in self.elements:
            element.replace_defines_in_braces(single_defines_reference)
    
    def process_typedef_array_rte_h(self, input_typ, single_def_ref,typdef_sturct_ref,input_array_info= []):
        ret = None 
        for key in single_def_ref:
            if "[" not in key:
                continue
            key_without_braces = key.split("[")[0]
            if input_typ == key_without_braces:
                length = int(key.split("[")[1].split("]")[0])
                typ = single_def_ref[key]
                input_array_info.append(length)
                found = self.search_type_in_ref(typ,single_def_ref,typdef_sturct_ref)
                if type(found) == C_struct:  
                    found.name = self.name  # typedef 어레이로 행렬로 선언하면 맨처음 행렬 정보가 날아감
                    found.array_info += input_array_info
                    found.IsArray = True
                    ret = found
                    break
                elif found in self.platform_type:
                    self.type = found
                    self.type_size = self.platform_type[found]
                    self.size = self.platform_type[found]
                    self.IsSingle = True
                    self.IsArray = True
                    self.array_info += input_array_info
                else:
                    self.process_typedef_array_rte_h(typ,single_def_ref, typdef_sturct_ref,input_array_info)
                break
        return ret

    def find_platform_type(self,tmp,single_typedef_reference):
        recursion_depth = 0
        while tmp not in self.platform_type:
            if recursion_depth > self.recursion_depth:
                raise Exception ("recursion depth max")
            tmp = single_typedef_reference[tmp]
            recursion_depth += 1
        return tmp

    def replace_type(self,single_typedef_reference,typdef_sturct_ref,vector_enum_ref):
        element_index = 0
        if self.type in single_typedef_reference:
            self.type = single_typedef_reference[self.type]
        for element in self.elements:
            if not (element.IsEnum) or not element.IsPointer:
                typedef_array_process = None
                # if not (element.IsStruct):
                array_info = []
                typedef_array_process = element.process_typedef_array_rte_h(element.type, single_typedef_reference,typdef_sturct_ref,input_array_info=array_info)
                if typedef_array_process:
                    typedef_array_process.replace_type(single_typedef_reference,typdef_sturct_ref,vector_enum_ref)
                    self.elements[element_index] = typedef_array_process
                # try:
                index = 0
                if element.type in vector_enum_ref:
                    element.elements = vector_enum_ref[element.type]["instance"].elements
                    element.IsEnum =  True
                    element.IsVecEnum = True
                    if element.IsPointer:
                        element.size = 4
                        element.type_size = self.platform_type["uint32"]
                    else:
                        result = self.find_platform_type(element.type,single_typedef_reference)
                        element.type = result
                        element.type_size = self.platform_type[result]

                    continue
                elif element.type in single_typedef_reference: 
                    tmp = element.type
                    while tmp not in element.platform_type:
                        if index > element.recursion_depth:
                            raise Exception
                        tmp = single_typedef_reference[tmp]
                        index += 1
                    element.type = tmp
                    element.type_size = self.platform_type[tmp]
                
                elif element.IsStruct or element.IsUnion:
                    element.replace_type(single_typedef_reference,typdef_sturct_ref,vector_enum_ref)
                self.biggest_element_size = max(element.type_size,self.biggest_element_size)
                # except:
                #     raise Exception (f"check single tpyedef typ:{element.type}, name:{element.name} ")
            element_index += 1

    def update_symbol_hierachy(self,cparser, symbol_hierachy=""):
        if not symbol_hierachy:
            symbol_hierachy += self.name
        else:
            symbol_hierachy = symbol_hierachy +"." + self.name
        cparser.symbol_shortcut[symbol_hierachy] = self
        if self.HasBitfield:
            for bitfield_element in self.elements:
                for bitfield_var in bitfield_element.bitfield_info:
                    bitfield_symbol_hierachy = symbol_hierachy +"." +bitfield_var["name"]
                    copied_bitfield_element = pickle.loads(pickle.dumps((bitfield_element)))
                    copied_bitfield_element.name = bitfield_var["name"]
                    copied_bitfield_element.bitfield_mask = bitfield_var["mask"]
                    cparser.symbol_shortcut[bitfield_symbol_hierachy] = copied_bitfield_element
        self.symbol_hierachy = symbol_hierachy
        if not self.IsEnum:
            for element in self.elements: 
                element.update_symbol_hierachy(cparser,symbol_hierachy)

    def shift_all_element_by(self,shifting_value):
        buff = []
        if self.IsStruct or self.IsUnion:
            for element in self.elements:
                element.address = hex(int(element.address, base = 16) + shifting_value )
                element.shift_all_element_by(shifting_value)
                buff.append(element)
        else:
            for element in self.elements:
                buff.append(element)
                    
         
        self.elements = buff
        
    def find_instance_at_index(self,index_info):
        offset = 1
        ret = False
        maximum_length = 1
        for index in index_info:
            offset *= int(index)
        for index in self.array_info:
            maximum_length *= index
        if offset > maximum_length:
            raise Exception (f"{self.name} index exceed maximum length")
            
        tmp_self = pickle.loads(pickle.dumps((self)))
        for index in index_info:
            tmp_self.name += f"[{index}]" 
        tmp_self.size = tmp_self.type_size
        tmp_self.address =  hex(int(tmp_self.address, 16) + tmp_self.type_size * offset)
        tmp_self.shift_all_element_by(tmp_self.type_size * offset)
        tmp_self.array_info = []
        tmp_self.num_of_array = 1
        tmp_self.IsArray = False
        ret = tmp_self
        return ret

    def duplicate_self_array(self):
        ret = []
        if self.IsArray:
            for index in range(self.num_of_array):
                tmp_self = pickle.loads(pickle.dumps((self)))
                # tmp_self.duplicate_array_self()
                array_text =""
                
                for array_info_index in range (len(tmp_self.array_info)): #일단 이중배열만 복사
                    if len(tmp_self.array_info) == 2:
                        if array_info_index == 0:
                            array_text += f"[{int(index/tmp_self.array_info[-1])}]"
                        else:
                            array_text += f"[{int(index%tmp_self.array_info[array_info_index])}]"
                    elif len(tmp_self.array_info) >3:
                        raise Exception ("not yet support 3d array")
                    else:
                        if type(tmp_self.array_info[array_info_index]) != int:
                            tmp_self.array_info[array_info_index] = int(tmp_self.array_info[array_info_index])
                        array_text += f"[{int(index%tmp_self.array_info[array_info_index])}]"
                        
                tmp_self.name += array_text 
                tmp_self.size = tmp_self.type_size
                tmp_self.address =  hex(int(tmp_self.address, base=16) + tmp_self.type_size*index)
                tmp_self.shift_all_element_by( tmp_self.type_size*index)
                tmp_self.array_info = []
                tmp_self.num_of_array = 1
                tmp_self.IsArray = False
                ret.append(tmp_self)
        return ret
        
    def duplicate_array_element(self):
        buff = []
        for element in self.elements:
            if element.IsArray:
                for index in range(element.num_of_array):
                    tmp_element = pickle.loads(pickle.dumps((element)))
                    tmp_element.duplicate_array_element()
                    array_text =""
                    
                    for array_info_index in range (len(tmp_element.array_info)): #일단 이중배열만 복사
                        if len(tmp_element.array_info) == 2:
                            if array_info_index == 0:
                                array_text += f"[{int(index/tmp_element.array_info[-1])}]"
                            else:
                                array_text += f"[{int(index%tmp_element.array_info[array_info_index])}]"
                        elif len(tmp_element.array_info) >3:
                            raise Exception ("not yet support 3d array")
                        else:
                            array_text += f"[{int(index%tmp_element.array_info[array_info_index])}]"
                            
                    tmp_element.name += array_text 
                    # tmp_element.elements = element.elements
                    tmp_element.size = tmp_element.type_size
                    tmp_element.address = hex(int(element.address, 16) + tmp_element.type_size*index)
                    tmp_element.shift_all_element_by(tmp_element.type_size*index)
                    tmp_element.array_info = []
                    tmp_element.num_of_array = 1
                    tmp_element.IsArray = False
                    buff.append(tmp_element)

            else:
                element.duplicate_array_element()
                buff.append(element)
        self.elements  = buff
        
    def update_elements_size(self ,addr_offset = 0):   #배열은 무조건 연속으로 배치된다는 가정하에 짠다
        if (self.IsStruct or self.IsUnion) and not self.IsPointer:
            # copied_elements = pickle.loads(pickle.dumps((self.elements)))
            dq = deque(self.elements)
            dq.reverse()
            aligndq = deque()
            ElemntsHasBitfield = False
            tmp = 0
                
            while dq:
                head = dq[-1] 
                if head.HasBitfield:
                    ElemntsHasBitfield = True
                if not head.padded:
                    head.update_elements_size() #확인처리필요
                if self.biggest_element_size <4:  # if self.biggest_element_size >= 4case need word aligning and padding
                    if head.IsStruct or head.IsUnion and not head.IsPointer:
                        if head.HasBitfield:
                            if (tmp) % 4 != 0: #word align
                                tmp+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()
                        elif head.biggest_element_size == 4:
                            if (tmp) % 4 != 0: #word align
                                tmp+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()
                        elif head.type_size == 1: #structure 크기가 1바이트면 노얼라인
                            if (tmp) % 1 != 0:
                                tmp+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()
                        elif head.type_size >= 8: #structure 크기가 8byte 이상이면 4바이트 얼라인 word align
                        
                            if (tmp) % 4 != 0: #word align
                                tmp+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()
                        else:  #structure 크기가 그게아닐때는 2바이트 얼라인
                            if (tmp) % 2  != 0:
                                tmp+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()
                    elif head.IsSingle or head.IsEnum:
                        if head.type_size == 4: 
                            if (tmp) % 4 != 0:
                                tmp+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()
                        elif head.type_size == 2: #8byte 이상이면 4바이트 얼라인 word align
                        
                            if (tmp) % 2 != 0: #word align
                                tmp+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()
                        else:  
                            if (tmp) % 1  != 0:
                                tmp+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()

                else:
                    if head.IsStruct or head.IsUnion and not head.IsPointer:
                        if head.type_size == 1: #structure 크기가 1바이트면 노얼라인
                            if (tmp) % 4 != 0:
                                tmp+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()
                        elif head.type_size >= 8: #structure 크기가 8byte 이상이면 4바이트 얼라인 word align
                            if (tmp) % 4 != 0: #word align
                                tmp+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()
                        else:  #structure 크기가 그게아닐때는 2바이트 얼라인
                            if (tmp) % 2  != 0:
                                tmp+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()
                    elif head.IsSingle or head.IsEnum:
                        if head.type_size == 4: 
                            if (tmp) % 4 != 0:
                                tmp+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()
                        elif head.type_size == 2: 
                            if (tmp) % 2 != 0: #word align
                                tmp+=1
                                # addr+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()
                        else:  
                            if (tmp) % 1  != 0:
                                tmp+=1
                                # addr+=1
                            else:
                                head.address = tmp
                                tmp += head.size
                                dq.pop()
            if self.biggest_element_size >=4 or ElemntsHasBitfield:
                while tmp%4 !=0:
                    tmp+=1
            elif tmp > 1 and tmp <= 7:
                while tmp%2 !=0:
                    tmp+=1
            elif tmp > 7:
                while tmp%4 !=0:
                    tmp+=1
            # aligndq.reverse()
            # self.elements = list(aligndq)
            self.type_size = tmp
            self.size = tmp * self.num_of_array
        elif self.IsSingle:
            if self.IsArray:
                self.size = self.type_size * self.num_of_array
            else:
                self.size = self.type_size
        elif self.IsPointer:
            if self.IsArray:
                self.size = self.type_size * self.num_of_array
            else:
                self.size = self.type_size
        elif self.IsEnum:
            self.type_size = 4
            self.size = self.type_size * self.num_of_array
        self.padded = True

    def update_elements(self, typedef_reference):
        if (self.IsStruct or self.IsEnum or self.IsUnion):
            buff = []
            for element in self.elements:
                if element.type in typedef_reference and not element.IsPointer:
                    tmp = pickle.loads(pickle.dumps(typedef_reference[element.type]["instance"]))
                    tmp.name = element.name
                    tmp.IsArray = element.IsArray
                    tmp.array_info = element.array_info
                    tmp.update_elements(typedef_reference)
                    buff.append(tmp)
                else:
                    self.biggest_element_size = max(self.biggest_element_size,element.size)
                    if element.bitfield:
                        self.process_bitfield(buff)   
                        self.HasBitfield = True
                        # self.bitfield = True
                        break
                    else:
                        element.update_elements(typedef_reference )
                    
                    buff.append(element)
            if self.biggest_element_size == 0:
                self.biggest_element_size = 1

            self.elements = buff
        
            
    def process_bitfield(self,buff):#bit field 현재코드에서만 동작함
        bit_field_name = []
        bit_field_size = []
        bit_field_type = []
        local_buff = []
        bit_cnt = 0
        for element in self.elements:
            bit_field_name.append(element.name)
            bit_field_size.append(element.bitfield)
            bit_field_type.append(element.type)
            bit_cnt += element.bitfield
        if bit_cnt <8:
            bit_cnt_to_byte = 1
        else: 
            if bit_cnt % 8 == 0:
                bit_cnt_to_byte= int(bit_cnt/8)
            else:
                bit_cnt_to_byte= int(bit_cnt/8)+1
        for _ in range(bit_cnt_to_byte):
            copy_element = pickle.loads(pickle.dumps(self.elements[0]))
            copy_element.size = 1
            copy_element.type_size = 1
            copy_element.name = "bit fxxking field"

            local_buff.append(copy_element)
        bit_cnt_index= 0
        mask = 0
        for index in range(len(bit_field_size)):
                            # mask += pow(2,( (bit_cnt-1-bit_cnt_index)-power))
            mask = 0
            mask += pow(2,bit_field_size[index])-1

            mask *= pow(2,bit_cnt_index)
            local_buff[int(bit_cnt_index /8)].bitfield_info.append(\
                                                    {\
                                                    "name":bit_field_name[index],\
                                                    "type":bit_field_type[index],\
                                                    "mask":mask \
                                                    }\
                                            )
            bit_cnt_index += bit_field_size[index]
        
        buff += local_buff
        self.type_size = len(local_buff)
        self.size = len(local_buff)
        self.biggest_element_size = 1
        return True
        
    def add_struct_element(self,input_C_struct):
        self.elements.append(input_C_struct)
        
    def __repr__(self) -> str:
        return f"{self.type},{self.name},{self.array_info},{self.address},{self.size}"
    
    class struct_padding:
        def __init__(self,c_type= "#padding",name= "#padding",size= 1):
            self.size = size
            self.c_type = c_type
            self.name = name
            self.IsBitfield = False
            self.IsPadding = False
            self.IsArray = False
            self.IsStruct = False
            self.IsSingle = True
            if c_type == "#padding":
                self.IsPadding = True
            else:
                self.IsBitfield = True

