# edge_test_utils.py 

# from standard library
import os
import re
import json
import copy
import difflib
import hashlib
import importlib
import inspect
from pprint import pformat
#import contextlib
from functools import wraps
from typing import Dict, Any, List, Callable, Tuple, Optional

# non standard library imports are performed only if enabled, below.
# import coverage
# from utilities import pickledjson, args # utils, s3utils, 


class EdgeTestConfig:
    # the following setting is the minimum number of tests for a specific function.
    # but if it is found that any additional tests provide additional coverage in terms
    # of code coverage or output coverage (changes in output values) then it will add additional tests.
    test_count_limit = 10
    
    # when multi-line text is compared, exclude these patterns which are likely date and version information.
    text_exclusion_patterns = [
        r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}",  # ISO 8601 date pattern with microseconds
        r"version:\'v\d+\.\d+\.\d+ \(\w{7}\)\'",        # Version pattern like 'v2.23.X (78a0796)'
        ]

    enable_edge_tests = False
    
    test_cases_folder = 'edge_test_cases'
    
    @classmethod
    def enable(cls):
        cls.enable_edge_tests = True
    
    @classmethod
    def disable(cls):
        cls.disable_edge_tests = True


import warnings

def disable_resource_warnings():
    """Disable resource warnings."""
    warnings.filterwarnings('ignore', category=ResourceWarning)
    
def disable_deprecation_warnings():
    """Disable deprecation warnings."""
    warnings.filterwarnings('ignore', category=DeprecationWarning)    

def clean_vars(these_args):
    these_vars = {}
    for var_name, var_value in these_args.items():
        if not var_name.startswith('__') \
                and var_name not in ('func', 'wraps', 'save_edge_tests', 'clean_vars') \
                and not inspect.ismodule(var_value):
            these_vars[var_name] = var_value
    return these_vars


def save_edge_tests(state:Optional[Any]=None):
    """
    Decorator for saving edge test cases.

    This decorator is used to wrap functions and save their inputs and outputs as test cases.
    It creates a folder named 'test_cases' (or uses an existing one) to store the test cases.
    Test cases are saved as pickle files in subfolders named after the function they belong to.
    Each test case file contains the module name, function name, inputs, and outputs.
    
    Each test case is named using the md4 hash digest of the flattened input args, kwargs, and other state.

    Args:
        state (dict, optional): if provided, this dict provides the name of the local state to be reproduced.
            save_edge_tests will fill in the value of the key provided with the value present when the function is called.

    Returns:
        Creates test data at edge_test_cases/{module}/{function_name}/{hexdigest based on inputs}.json
    
        function: The decorated function.

    Example:
        @edge_test_utils.save_edge_tests()
        def my_function(arg1, arg2):
            return arg1 + arg2

        # This will save edge test cases for 'my_function' in the 'test_cases' folder.
        
        # if args.argsdict is used inside the function, this state must be established.
        
        @edge_test_utils.save_edge_tests(state={'args.argsdict': None})
        def my_function(arg1, arg2):
            return arg1 + arg2 + args.argsdict['value']
            
            
    """


    def decorator(func):
        func_name = func.__name__

        @wraps(func)
        def wrapper(*my_args, **kwargs):
        
            if not EdgeTestConfig.enable_edge_tests:
                # If saving is not enabled, simply call the wrapped function
                return func(*my_args, **kwargs)
                
            import coverage
            import jsonpickle
            from utilities import args # pickledjson, utils, s3utils,

            if not os.path.exists(EdgeTestConfig.test_cases_folder):
                os.makedirs(EdgeTestConfig.test_cases_folder)

            # here, can add check on argsdict flag to enable or config
            # class that enables the wrapper.            

            pre_args_copy = copy.deepcopy(my_args)
            pre_kwargs_copy = copy.deepcopy(kwargs)
            
            # Save global variables
            # global_vars = clean_vars(globals())
           
            # Initialize coverage
            cov = coverage.Coverage()
            cov.start()

            result = func(*my_args, **kwargs)

            # Stop and save coverage
            cov.stop()
            cov.save()

            func_def, docstring = capture_function_details(func)
            module_name = func.__module__
            func_dirpath = os.path.join(EdgeTestConfig.test_cases_folder, module_name, func_name)
                
            try:
                os.makedirs(func_dirpath)   # Recursive directory creation function. Like mkdir(), but makes all intermediate-level directories needed to contain the leaf directory.
                                            # Raises an error exception if the leaf directory already exists or cannot be created.
            except Exception:
                pass
               
            # # Count existing cases
            # num_existing_cases = len([f for f in os.listdir(func_dirpath) if f.endswith('.json')])
                
            # Save inputs, function name, module name, and outputs
            test_data = {
                'module_name':      module_name,
                'func_name':        func_name,
                'func_def':         func_def.splitlines(),  # make these easier to read in json.
                'docstring':        docstring.splitlines(),
                #'global_vars':      global_vars,
                'pre_args':         list(pre_args_copy),    # convert from tuple to list
                'pre_kwargs':       pre_kwargs_copy,
                }

            if state:
                if 'args.argsdict' in state:
                    state['args.argsdict'] = args.argsdict
                test_data['state'] = state
                    
            # create the test data with no result included, with md5 hash to be used as the file name
            flattened_data_no_result = jsonpickle.encode(test_data, keys=True, use_base85=True, indent=4)
            
            #flattened_data_no_result = pickledjson.serialize(test_data, indent=4)
            md5hash = hashlib.md5(flattened_data_no_result.encode("utf-8")).hexdigest()
            testcase_path = os.path.join(func_dirpath, f"{md5hash}.json")
                
            # now add the results of the call.
            test_data['post_args']      = list(my_args)           # convert from tuple to list
            test_data['post_kwargs']    = kwargs
            test_data['result']         = result

            # jsonable_test_data = pickledjson.convert_to_jsonable(test_data)
            flattened_data = jsonpickle.encode(test_data, keys=True, use_base85=True, indent=4)
            
            # # add printable version of each field that has been pickled.
            # for field in ('pre_args', 'pre_kwargs', 'post_args', 'post_kwargs', 'result'):
                # if '__PICKLED__' in jsonable_test_data.get(field, ''):
                    # jsonable_test_data[f"printable_{field}"] = pprint.pformat(test_data[field]).splitlines()

            # # Serialize the object to JSON
            # flattened_data = json.dumps(jsonable_test_data, indent=4)
            
            executed_lines_in_function = get_executed_lines(cov, func)
            
            # Load existing coverage data
            coverage_path = os.path.join(func_dirpath, 'coverage.json')
            if os.path.exists(coverage_path):
                with open(coverage_path, 'r') as f:
                    coverage_data = json.load(f)
            else:
                coverage_data = {'code_coverage': [], 'output_coverage': {'tested': None}}

            # Analyze output differences
            diff_report, coverage_data['output_coverage']['tested'] = compare_objects(
                coverage_data['output_coverage'].get('result', None),
                result,
                coverage_data['output_coverage'].get('tested', None)
            )

            # Update code coverage
            coverage_data['code_coverage'] = list(set(coverage_data['code_coverage']).union(set(executed_lines_in_function)))

            # Check if new test case should be saved
            
            should_save_test = False
            if len(os.listdir(func_dirpath)) < EdgeTestConfig.test_count_limit + 1:
                should_save_test = True
            elif set(executed_lines_in_function).difference(set(coverage_data['code_coverage'])):
                should_save_test = True
            elif contains_false(coverage_data['output_coverage'].get("tested")):
                should_save_test = True
             
            if should_save_test:
                # Save test data
                with open(testcase_path, 'w') as f:
                    f.write(flattened_data)

                # Save updated coverage data
                with open(coverage_path, 'w') as f:
                    json.dump(coverage_data, f, indent=4)

            return result
        
        return wrapper
    
    return decorator


def contains_false(value: Any) -> bool:
    """
    Recursively checks if the given value contains any False boolean.
    
    Args:
    value (Any): The value to check. Can be a dict, list, or bool.
    
    Returns:
    bool: True if any nested value is False, otherwise False.
    """
    if isinstance(value, bool):
        return not value
    elif isinstance(value, dict):
        for v in value.values():
            if contains_false(v):
                return True
        return False
    elif isinstance(value, list):
        for v in value:
            if contains_false(v):
                return True
        return False
    return False

   
def get_executed_lines(cov, func):
    """ Return the lines executed in the function of interest.
    
    Note that cov object has CoverageData and it uses non-normalized module names, 
        which may not match inspect. pathname for the module. The function 
        matches them up by normalizing the keys and uses that to get the lines,
        then filters the lines per func_lines_range().
    """
    source_lines, start_line = inspect.getsourcelines(func)
    func_lines_range = range(start_line, start_line + len(source_lines))
    norm_module_path = os.path.normcase(inspect.getfile(func))
            
    cov_filepaths = list(cov.get_data()._file_map.keys())

    norm_cov_filepaths = [os.path.normcase(path) for path in cov_filepaths]
    
    try:
        cov_filepath = cov_filepaths[norm_cov_filepaths.index(norm_module_path)]
    except ValueError:
        print(f"Can't find module {norm_module_path} in {norm_cov_filepaths} in save_edge_tests decorator.")
        raise
            
    # Get the total lines covered by the coverage data
    covered_lines = cov.get_data().lines(cov_filepath)

    if covered_lines is None:
        breakpoint()    # perm ok
        pass

    # Filter executed lines to those within the function's line range
    # Filter the covered lines to those within the function's line range
    executed_lines_in_function = [
        line for line in covered_lines
            if line in func_lines_range
        ]
        
    return executed_lines_in_function


    

def apply_test_cases():

    # sockets left open occurs sometimes when individual functions are called.
    disable_resource_warnings()
    disable_deprecation_warnings()

    modules = os.listdir(EdgeTestConfig.test_cases_folder)
    
    print(f"Tests for {len(modules)} modules found.")

        
    for module_dirname in modules:
        
        module_dirpath = os.path.join(EdgeTestConfig.test_cases_folder, module_dirname)
        
        function_dirs = os.listdir(module_dirpath)

        print(f"Tests for {len(function_dirs)} functions found for module {module_dirname}.")
        
        for function_dirname in function_dirs:
        
            func_dirpath = os.path.join(module_dirpath, function_dirname)
            
            case_files = os.listdir(func_dirpath)
            
            print(f"# Running edge tests for {module_dirname}/{function_dirname}, {len(case_files)} tests found.")
        
            for case_file in case_files:
                if not case_file.endswith('.json') and case_file != 'coverage.json':
                    continue
            
                #s3utils.close_s3_connections()

                edge_test_path = os.path.join(func_dirpath, case_file)
                
                apply_edge_test_at_path(edge_test_path, break_on_error=False)



def apply_edge_test_at_path(edge_test_path: str, break_on_error: bool=False, print_details: bool=False) -> bool:


    from utilities import args # utils, s3utils, pickledjson, 

    import jsonpickle

    with open(edge_test_path, 'r') as f:
        case_data_json = f.read()
        
    #case_data = pickledjson.deserialize_value(case_data_json)
    case_data = jsonpickle.decode(case_data_json, keys=True, on_missing='error')
    
    # Establish global variables
    if 'global_vars' in case_data:
        for var_name, var_value in case_data['global_vars'].items():
            globals()[var_name] = var_value

    module_name             = case_data['module_name']
    func_name               = case_data['func_name']
    pre_args                = case_data['pre_args']
    pre_kwargs              = case_data['pre_kwargs']
    expected_post_args      = case_data['post_args']
    expected_post_kwargs    = case_data['post_kwargs']
    expected_result         = case_data['result']
    state                   = case_data.get('state', {})
    
    print(f"- Testing '{module_name}.{func_name}'\n   - Test File: '{edge_test_path}'")
    
    # Find the module file
    module_file = importlib.util.find_spec(module_name).origin

    # Import the module dynamically
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    if 'args.argsdict' in state:
        args.argsdict = state['args.argsdict']
    else:    
        if 'argsdict' in pre_kwargs:
            args.argsdict = pre_kwargs['argsdict']

    # Get the function dynamically
    function = getattr(module, func_name)

#    import io
#    f = io.StringIO()
#    with contextlib.redirect_stdout(f):
        # Call the function with the saved inputs
    actual_result = function(*pre_args, **pre_kwargs)
#    stdout_str = f.getvalue()
    stdout_str = ''

    # naming convenience.
    actual_post_args = pre_args
    actual_post_kwargs = pre_kwargs
    # Assert that the result matches the expected output
    # self.assertEqual(result, expected_output)
    # self.assertEqual(pre_args, post_args)
    # self.assertEqual(pre_kwargs, post_kwargs)
    result_report   = compare_objects(expected_result, actual_result)
    args_report     = compare_objects(expected_post_args, actual_post_args)
    kwargs_report   = compare_objects(expected_post_kwargs, actual_post_kwargs)
    
    if not (result_report or 
            args_report or  
            kwargs_report
        ):
        print(f"   - OK: Result matches expected output. stdout not compared: {len(stdout_str)} chars.\n")
        return True
    else:
        print("## ERROR: Result does not match expected output")
        print(f"- expected_post_args == actual_post_args?     {bool(not args_report)}")
        print(f"- expected_post_kwargs == actual_post_kwargs? {bool(not kwargs_report)}")
        print(f"- actual_result == expected_result?           {bool(not result_report)}")
        if print_details:
            if not args_report:
                # print(f"### expected_post_args:\n{  pprint.pformat(expected_post_args, indent=4, sort_dicts=False)}")
                # print(f"### actual_post_args:\n{    pprint.pformat(actual_post_args, indent=4, sort_dicts=False)}\n\n")
                print(f"### post_args difference_report: expected -> actual\n{args_report}\n")
            if kwargs_report:
                # print(f"### expected_post_kwargs:\n{pprint.pformat(expected_post_kwargs, indent=4, sort_dicts=False)}")
                # print(f"### actual_post_kwargs:\n{  pprint.pformat(actual_post_kwargs, indent=4, sort_dicts=False)}\n\n")
                print(f"### post_kwargs difference_report: expected -> actual\n{kwargs_report}\n")
            if result_report:
                # print(f"### expected_result:\n{     pprint.pformat(expected_result, indent=4, sort_dicts=False)}\n")
                # print(f"### actual_result:\n{       pprint.pformat(actual_result, indent=4, sort_dicts=False)}\n")
                print(f"### result difference_report: expected -> actual\n{result_report}\n")
                
        if break_on_error:
            # this breakpoint lets the developer inspect the variables.
            breakpoint() # perm
        
    return False
    
    
def difference_report(expected_result, actual_result):

    return "\n".join(compare_objects(obj1=expected_result, obj2=actual_result))
    

# Helper functions for comparison
    
def compare_objects(obj1: Any, obj2: Any, tested: Any, path: str = '') -> Tuple[List[str], Any]:
    """
    Compares two objects (dictionaries, lists, or scalar values) and provides a detailed difference report.
    
    Args:
    obj1 (Any): The first object to compare.
    obj2 (Any): The second object to compare.
    tested (Any): The structure indicating which parts have been tested.
    path (str): The current path of the nested key being compared.
    
    Returns:
    Tuple[List[str], Any]: A tuple containing the difference report and the updated tested structure.
    
    RECURSIVE
    """
    report_lines: List[str] = []
    
    if obj1 == obj2:
        return report_lines, tested
    
    if isinstance(obj1, dict) and isinstance(obj2, dict):
        diff_lines, tested = compare_dicts(obj1, obj2, tested, path)
        report_lines.extend(diff_lines)
    elif isinstance(obj1, list) and isinstance(obj2, list):
        diff_lines, tested = compare_lists(obj1, obj2, tested, path)
        report_lines.extend(diff_lines)
    elif isinstance(obj1, str) and isinstance(obj2, str) and ('\n' in obj1 or '\n' in obj2):
        try:
            cleaned_obj1 = exclude_patterns(obj1)
            cleaned_obj2 = exclude_patterns(obj2)
        except Exception:
            breakpoint()    # perm ok
            
        if cleaned_obj1 != cleaned_obj2:
            report_lines.extend(compare_multiline_strings(cleaned_obj1, cleaned_obj2, path))
            report_lines.append(f"Modified {path}: {pformat(obj1, sort_dicts=False)} -> {pformat(obj2, indent=4, sort_dicts=False)}")
            tested = True
    elif obj1 != obj2:
        report_lines.append(f"Modified {path}: {pformat(obj1, sort_dicts=False)} -> {pformat(obj2, indent=4, sort_dicts=False)}")
        tested = True
    
    return report_lines, tested

def compare_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any], tested: Dict[str, Any], path: str = '') -> Tuple[List[str], Dict[str, Any]]:
    """
    Compares two dictionaries and provides a detailed difference report while preserving the order of keys.
    
    Args:
    dict1 (Dict[str, Any]): The first dictionary to compare.
    dict2 (Dict[str, Any]): The second dictionary to compare.
    tested (Dict[str, Any]): The structure indicating which parts have been tested.
    path (str): The current path of the nested key being compared.
    
    Returns:
    Tuple[List[str], Dict[str, Any]]: A tuple containing the difference report and the updated tested structure.
    
    RECURSIVE
    """
    if tested is None:
        tested = {}
    report_lines: List[str] = []
    keys = list(dict1.keys()) + [k for k in dict2.keys() if k not in dict1]
    
    for key in keys:
        current_path = f"{path}.{key}" if path else key
        if key not in dict1:
            report_lines.append(f"Added {current_path}: {pformat(dict2[key], indent=4, sort_dicts=False)}")
            tested[key] = True
        elif key not in dict2:
            report_lines.append(f"Removed {current_path}: {pformat(dict1[key], indent=4, sort_dicts=False)}")
            tested[key] = True
        else:
            if key not in tested:
                tested[key] = None
            diff_lines, tested[key] = compare_objects(dict1[key], dict2[key], tested[key], current_path)
            report_lines.extend(diff_lines)
    
    return report_lines, tested

def compare_lists(list1: List[Any], list2: List[Any], tested: List[Any], path: str = '') -> Tuple[List[str], List[Any]]:
    """
    Compares two lists and provides a detailed difference report.
    
    Args:
    list1 (List[Any]): The first list to compare.
    list2 (List[Any]): The second list to compare.
    tested (List[Any]): The structure indicating which parts have been tested.
    path (str): The current path of the nested key being compared.
    
    Returns:
    Tuple[List[str], List[Any]]: A tuple containing the difference report and the updated tested structure.
    
    RECURSIVE
    """
    report_lines: List[str] = []
    max_len = max(len(list1), len(list2))
    if tested is None:
        tested = [None] * max_len
    
    if len(tested) < max_len:
        tested.extend([None] * (max_len - len(tested)))

    for i in range(max_len):
        current_path = f"{path}[{i}]"
        if i >= len(list1):
            report_lines.append(f"Added {current_path}: {pformat(list2[i], indent=4, sort_dicts=False)}")
            tested[i] = True
        elif i >= len(list2):
            report_lines.append(f"Removed {current_path}: {pformat(list1[i], indent=4, sort_dicts=False)}")
            tested[i] = True
        else:
            diff_lines, tested[i] = compare_objects(list1[i], list2[i], tested[i], current_path)
            report_lines.extend(diff_lines)
    
    return report_lines, tested
    

def compare_multiline_strings(str1: str, str2: str, path: str = '') -> List[str]:
    """
    Compares two multi-line strings and provides a summary of the differences.
    
    Args:
    str1 (str): The first string to compare.
    str2 (str): The second string to compare.
    path (str): The current path of the nested key being compared.
    
    Returns:
    List[str]: A detailed report of the differences.
    """
    diff = list(difflib.unified_diff(str1.splitlines(), str2.splitlines(), lineterm=''))
    if diff:
        report_lines = [f"Modified {path}:\n" + '\n'.join(diff)]
    else:
        report_lines = []
    return report_lines


def exclude_patterns(text: str) -> str:
    """
    Excludes specific patterns from the text using regular expressions.
    
    Args:
    text (str): The text to be processed.
    
    Returns:
    str: The text with excluded patterns replaced.
    """
    if text is None:
        text = ''
    
    for pattern in EdgeTestConfig.text_exclusion_patterns:
        text = re.sub(pattern, "<excluded>", text)
    return text

def capture_function_details(func: Callable) -> Tuple[str, str]: 
    """
    Captures the function definition, docstring, function line range, and norm_module_path.
    
    Args:
    func (Callable): The function whose details are to be captured.
    
    Returns:
    Tuple[str, str, range, str]: A tuple with the function definition, docstring.
    """
    source_code =inspect.getsource(func)
    func_def = get_func_def(source_code)
    docstring = inspect.getdoc(func) or ""
    
    return func_def, docstring
    
    
def get_func_def(source_code) -> str:
    """ Given source_code for the module where the function exists,
        extract the function definition through either ':'
        or ' -> typehints:'
    """
    
    # Regex pattern to match the function definition
    function_pattern = re.compile(
        r'^.*(def\s+\w+\s*\(.*?\)\s*(?:->\s*[\w\[\],\s]*)*:[^\n]*).*$',
        re.DOTALL)
    match = function_pattern.search(source_code)
   
    if match:
        func_def = match.group(1)
    else:
        raise ValueError("Function definition not found.")
        
    func_def = func_def.strip(" \n\r")    

    return func_def