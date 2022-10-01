import sys
from pathlib import Path
from package.a2l_writer import A2L_Writer
from package.exl_reader import Exl_reader
from package.cparser import Cparser
from package.tableprinter import TablePrinter
from package.report_writer import write_report
from package.asap_template import intro_str
import time
import warnings
import pickle
import json
import gzip
warnings.filterwarnings("ignore")




def run_a2lmaker(pathinfo, arginfo):
    start = time.time()
    print(intro_str)
    path_project, exl_file, mapxml_file , report_file, path_strgsysjson, path_build = set_project_path(pathinfo,arginfo)
    cparser = Cparser(path_project,pathinfo)
    pickled_cparser = pickle.dumps(cparser)
    excel_reader = Exl_reader(exl_file)
    excel_reader.read()
    a2l_result = []
    history = {}
    warning_dict = {}

    for mapxml in mapxml_file:
        cparser = pickle.loads(pickled_cparser)
        cparser.read_ecu_type(mapxml)
        cparser.make_references()
        cparser.process_source(mapxml)
        cparser.process_with_map(mapxml)
        history[mapxml.name] = cparser
        #symbol file output 추가 예정
        # with gzip.open(f'{path_build.as_posix()}/{mapxml.stem}.sym', 'wb') as f:
        #     pickle.dump(cparser.symbol_shortcut, f)
    for mapxml in mapxml_file:
        warning_result = []
        cparser = history[mapxml.name]
        a2l = A2L_Writer(
            cparser, excel_reader, mapxml, path_strgsysjson,pathinfo,history,
            a2l_result = a2l_result, warning_result = warning_result,
        )
        warning_dict[a2l.actuator_name] = warning_result
    write_report(report_file, a2l_result, warning_dict,exl_file)
    print(TablePrinter(ul='-')(a2l_result,colors=True))
    print(f"\nDone in {(time.time() - start):.4} s")

    
def main():
    pass
    
    
if __name__ == "__main__":
    sys.exit(main())
