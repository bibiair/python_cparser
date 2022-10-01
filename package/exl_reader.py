from openpyxl import load_workbook
from library.colorama import init, Fore, Back, Style
class Exl_reader:
    def __init__(self,exl_file):
        self.new_to_parse = {}
        self.replace_static_variables = {}
        self.exl_bottom = {}
        self.exl_path = exl_file
        self.exl_info = []
        self.a2l_group_info = {}
        init(autoreset=True)
        try:
            self.pyxl_wb = load_workbook(filename = self.exl_path)
            self.pyxl_sh = self.pyxl_wb["A2L"]
        except:
            raise Exception("\nCannot open xlsx file " +self.exl_path.as_posix())
        # print("Successfully loaded xlsx file")
    def read(self):
        print(f"Reading xlsx file ...  ",end="")
        for row_index in range(3000):
            if row_index == 0:
                continue
            row_index = str(row_index+1)
            swc = self.pyxl_sh['A'+row_index].value
            group1 = self.pyxl_sh['B'+row_index].value
            group2 = self.pyxl_sh['C'+row_index].value
            group3 = self.pyxl_sh['D'+row_index].value
            a2l_Name = self.pyxl_sh['E'+row_index].value
            symbol_name = self.pyxl_sh['F'+row_index].value
            a2ltype = self.pyxl_sh['G'+row_index].value
            common_axis_x = self.pyxl_sh['H'+row_index].value
            conv_x = self.pyxl_sh['I'+row_index].value
            common_axis_y = self.pyxl_sh['J'+row_index].value
            conv_y = self.pyxl_sh['K'+row_index].value
            compu_method = self.pyxl_sh['L'+row_index].value
            comment = self.pyxl_sh['M'+row_index].value
            if not symbol_name:
                continue
            if swc:
                if swc.split("."):
                    swc = swc.split(".")[0]\
            
            a2l_group = []
            for group in [group1,group2,group3]:
                if group:
                    a2l_group.append(group)
            
            self.exl_info.append(\
                {\
                    "SWC" :swc,\
                    "GROUP" : a2l_group,\
                    "A2L_Name" :a2l_Name,\
                    "SYMBOL_NAME" :symbol_name,\
                    "A2LTYPE" :a2ltype,\
                    "A2L_GROUP" : a2l_group[::-1],\
                    "COMMENT" :comment,\
                    "common_axis_x" : common_axis_x,\
                    "conv_x" : conv_x,\
                    "common_axis_y" : common_axis_y,\
                    "conv_y" : conv_y,\
                    "compu_method" : compu_method,\
                }\
            )

            self.exl_info = sorted(self.exl_info, key = lambda x : x["A2LTYPE"])
            
        self.pyxl_wb.close()
        
        print(Fore.GREEN + "Done")
        return self.exl_info

            
                

