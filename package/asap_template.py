from library.colorama import init, Fore, Back, Style




item = """{indent}/begin {ID} {ID_NAME} {comment}{others}
{contents}{indent}/end {ID}\n"""
table_element = """{indent}{value1} {value1} "{string_repr}"\n"""
table_element_vtab = """{indent}{value1} "{string_repr}"\n"""
sub_item = """{indent}/begin {ID}
{contents}{indent}/end {ID}"""

group_root = """{indent1}/begin GROUP {group_name} ""\n{indent2}ROOT\n{sub_group}{indent1}/end GROUP\n"""
group = """{indent1}/begin GROUP {group_name} ""\n{sub_group}{indent1}/end GROUP\n"""
sub_group = """{indent1}/begin {sub_group_type}\n{indent2}{sub_group_elements}\n{indent1}/end {sub_group_type}\n"""
init(autoreset=True)
intro_str =Fore.BLUE +Style.BRIGHT + r"""
    ___   ___   __    __  ______    __ __ __________ 
   /   | |__ \ / /   /  |/  /   |  / //_// ____/ __ \
  / /| | __/ // /   / /|_/ / /| | / ,<  / __/ / /_/ /
 / ___ |/ __// /___/ /  / / ___ |/ /| |/ /___/ _, _/ 
/_/  |_/____/_____/_/  /_/_/  |_/_/ |_/_____/_/ |_|""" + Fore.RED + "DH\n\n"