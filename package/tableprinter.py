from library.colorama import init, Fore, Back, Style
class TablePrinter(object): 
    "Print a list of dicts as a table" 
    def __init__(self,sep= ' | ', printing_warning= False, ul=None, data_list= None): 
        """         
        @param fmt: list of tuple(heading, key, width) 
                        heading: str, column label 
                        key: dictionary key to value to print 
                        width: int, column width in chars 
        @param sep: string, separation between columns 
        @param ul: string, character to underline column label, or None for no underlining 
        """ 
        self.printing_warning = printing_warning
        super(TablePrinter,self).__init__()
        
        init(autoreset=True)
        if self.printing_warning:
            message_col_len = 0
            symbol_col_len = 0
            if data_list:
                for data in data_list:
                    message_col_len = max(len(data["message"]),message_col_len)
                for data in data_list:
                    symbol_col_len = max(len(data["symbol"]),symbol_col_len)
            else:
                message_col_len = 60
                symbol_col_len = 60
            fmt = [ 
            ('File',       'filename',   20), 
            ('Message',          'message',       message_col_len), 
            ('Symbol',          'symbol',       symbol_col_len), 
            ]
        else:
            fmt = [ 
            ('Filename',       'filename',   20), 
            ('Date',          'date',       19), 
            ('Warning', 'warning', 10), 
            ('Path',          'path',       63), 
            ]
        self.fmt   = str(sep).join('{lb}{0}:{1}{rb}'.format(key, width, lb='{', rb='}') for heading,key,width in fmt) 
        self.fmt_colors   = str(Fore.WHITE+sep).join('{lb}{0}:{1}{rb}'.format(key, width+5, lb='{', rb='}') for heading,key,width in fmt) 
        self.head  = {key:heading for heading,key,width in fmt} 
        self.ul    = {key:str(ul)*width for heading,key,width in fmt} if ul else None 
        self.width = {key:width for heading,key,width in fmt} 
        # print(self.print_table(data))
    
    def row(self, data,colors =True): 
        table = {}
        for k,w in self.width.items():
            space = ""
            if colors:
                w += 5
            table[k] = (data[k])[:w] + space
        if colors:
            return self.fmt_colors.format(**table) 
        else:
            return self.fmt.format(**table) 


    def __call__(self, dataList, colors = False, actuator_name = ""): 
        _r = self.row 
        res = [_r(data,colors = colors) for data in dataList] 
        res.insert(0, _r(self.head,colors=False)) 
        if self.ul: 
            res.insert(1, _r(self.ul,colors=False)) 
        if self.printing_warning:
            res.insert(0,(f"\n# WARNINGS {actuator_name}\n"))
        else:
            res.insert(0,( Fore.BLUE + "\nA2L RESULTS " + Fore.WHITE + "-"*109))
        return '\n'.join(res)