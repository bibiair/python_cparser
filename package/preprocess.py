from logging import raiseExceptions
from .filetool import (read_text, remove_c_comment,write_file,write_text)
import re
import enum
from copy import deepcopy
import io


def preprocessor_2(
    text,
    defined_dict={},
    save_defines=True,
    pattern_include=None,
    suppress_error = False,
):
    strNeedsPreprocessing = []
    unfound_defines = {}
    if not text:
        return defined_dict, text

    def check_condition(if_text, condition_text, defined_dict):
        def replace_condition_text(condition_text):
            def repl(m):
                macro = m.group()
                if macro in defined_dict:
                    return defined_dict[macro]
                else:
                    raiseExceptions (f"undefined {macro}")
                    

            def repl2(m):
                return m.group(1)

            condition_text = re.sub(
                r"\b[a-zA-Z_][a-zA-Z0-9_]*", repl, condition_text
            )
            condition_text = re.sub(r"\b(\d+)[LUF]\b", repl2, condition_text)
            if re.search(r"\b[a-zA-Z_][a-zA-Z0-9_]*", condition_text):
                # or re.search(r"\b[a-zA-Z_][a-zA-Z0-9_]*", condition_text)):
                return replace_condition_text(condition_text)
            return condition_text

        def check_if_text(if_text, condition_text):
            original_text = condition_text
            # skip -> else : True
            if if_text == "else":
                return True
            elif if_text == "ifndef":
                try:
                    condition_text = replace_condition_text(condition_text).strip()
                    return bool(condition_text)
                except:
                    return True
            elif if_text == "ifdef":
                try:
                    condition_text = replace_condition_text(condition_text).strip()
                    return not bool(condition_text)
                except:
                    return False
            else:
                try:
                    
                    condition_text = replace_condition_text(condition_text)
                    condition_text = condition_text.replace("||", "|").replace(
                        "&&", "&"
                    )
                    return eval(condition_text)
                except:
                    if "defined" in original_text:
                        return True
                    else:
                        print(f'cannot find option:"{original_text}"')
                    return False
                    # raise Exception (f'cannot find option:"{condition_text}"')

        return check_if_text(if_text, condition_text)

    def remove_sharp_if(text,strNeedsPreprocessing):
        def log_debugs(debugs, line, pre_state=[], if_state=[]):
            if pre_state or if_state:
                pre_state_text = "/".join(pre_state)
                state_text = "/".join(if_state)
                debugs.append(
                    line
                )
            else:
                debugs.append(line)
            return debugs

        def change_state(if_state, line, debugs, to_change="", to_append=""):
            pre_state = deepcopy(if_state)
            if to_change:
                if_state[-1] = to_change
            elif to_append:
                if_state.append(to_append)
            else:
                if_state.pop()
            debugs = log_debugs(debugs, line, pre_state, if_state)
            return if_state, debugs

        p_endif = re.compile(r"#[ ]*endif")
        p_elseif = re.compile(r"#[ ]*(?P<if>else|elif)(?P<condition>[^\n]*)")
        p_if = re.compile(r"#[ ]*(?P<if>ifndef|ifdef|if)(?P<condition>[^\n]*)")
        p_define = re.compile(
            r"""
            \#[ \t]*define[ \t]+
            \b(?P<key>\w+)[ \t]+
            [\( ]*(?P<val>[\w.\"]+)
            [^\n]*
            """,
            re.VERBOSE,
        )

        if_state = []  # doing, done, skip
        debugs = []
        doing_text = []

        # try:
        for _, line in enumerate(io.StringIO(text)):
            # line = line.strip()
            if len(line) == 1:
                if line[0] == "\n":
                    continue
            # 1. Looking for #endif
            if re.search(p_endif, line):
                change_state(if_state, line, debugs)
                continue

            # 2. Looking for #else, #elif
            m = re.search(p_elseif, line)
            if m:
                if len(if_state) > 1:
                    if "skip" in if_state[:-1] or "done" in if_state[:-1]:
                        log_debugs(debugs, line)
                        continue
                if if_state[-1] == "doing":
                    change_state(if_state, line, debugs, to_change="done")
                elif if_state[-1] == "skip":
                    if check_condition(
                        m.group("if"), m.group("condition"), defined_dict
                    ):
                        change_state(if_state, line, debugs, to_change="doing")
                    else:
                        log_debugs(debugs, line)
                continue

            # 4. Looking for the #if
            m = re.search(p_if, line)

            if m:
                if "skip" in if_state or "done" in if_state:
                    change_state(if_state, line, debugs, to_append="skip")
                elif check_condition(
                    m.group("if"), m.group("condition"), defined_dict
                ):
                    change_state(if_state, line, debugs, to_append="doing")
                else:
                    if_state, debugs = change_state(
                        if_state, line, debugs, to_append="skip"
                    )
                continue

            log_debugs(debugs, line)

            # 3. if not doing, skip this line
            if if_state and if_state[-1] != "doing":
                continue

            # 5. Looking for #error
            if re.search("#error", line):
                if suppress_error == False:
                    raise SyntaxError(line)
                else:
                    strNeedsPreprocessing += "".join(debugs)

            # 6. Looking for #define
            if save_defines:
                
                def save_define(m):
                    defined_dict[m.group("key")] = m.group("val")

                re.sub(p_define, save_define, line)
            # 7. doing
            doing_text.append(line)

        return "\n".join(doing_text)

        # except:
        #     # when crawling error occurs, write log file(crawling_error.h) for debug

        #     if line == debugs[-1]:
        #         debugs[-1] = f"{debugs[-1].rstrip()} // >> crawling error!"
        #     else:
        #         debugs.append(f"{line.rstrip()} // >> crawling error!")

        #     error_line_number = len(debugs)

        #     defined_text = f'\n\n{"/"*50} crawled ecu options - start\n'
        #     defined_text += (
        #         f"// ** check matching is correct with following files **\n"
        #     )
        #     defined_text += f"// 1. spec option json in BuildResource in Mineral\n"
        #     defined_text += f"// 2. ecu type.h\n"
        #     defined_text += f"// 3. your source file\n\n"
        #     for k, v in defined_dict.items():
        #         defined_text += f"// #define {k} {v}\n"
        #     defined_text += f'{"/"*50} crawled ecu options - end'
        #     debugs.append(defined_text)

    text = remove_sharp_if(text, strNeedsPreprocessing)
    text = re.sub(r"(?<!.)\n","",text) # remove meaningless \n

    return defined_dict, text, strNeedsPreprocessing