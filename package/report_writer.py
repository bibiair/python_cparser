from .tableprinter import TablePrinter
from .filetool import write_text
from .filetool import run_subprocess
def write_report( report_file, a2l_result, warning_dict,exl_file):
    report = ""
    report += "\n# Results\n\n"
    report += '"Excel file" : ' + exl_file.absolute().as_posix() +"\n\n"
    for result in a2l_result:
        filename = result["filename"][5:]
        warnings = result["warning"][5:]
        report += f"\"{filename}\" : {warnings} warnings\n"
        
    for actuator_name, warning_result in warning_dict.items():
        report += "\n"
        report += TablePrinter(printing_warning = True, ul='-', data_list= warning_result)(warning_result, colors=False,actuator_name = actuator_name)
        
    write_text(report_file , report)
    run_subprocess(f"code {report_file.absolute().as_posix()}")
