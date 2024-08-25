# edgetest

This package provides utilities and tools to implement edge testing of python functions/methods.

> Note: This has been recently split from another repo and may need some adjustments for general-purpose
use, however since it is early in the use of this package, it is primarily being developed in the
private audit-engine repo and can be updated to this public repo occassionally until it becomes a 
fully supported PyPI package that is promoted for general use.

Essentially, edgetest creates test data during actual operation of a decorated function, and
allows the test data to be replayed later.

A "test case" consists of 
    the function signature and docstring
    args and kwargs passed to the function
    any global data also required
    args and kwargs after the function completes, if they differ
    results of running the function

The test case is saved as JSON in a readable format, and it may also use additional files
for large input and output data items, such as images, dataframes, etc.

A test case is created only for unique input parameters of the function, and the test case is
named based on a hash of stringified input parameters. If saving tests is enabled, then unique
cases are saved upto the limit.

Once the limit is reached, then saving may continue if coverage increases (different paths are
used in the function). 
If the function is not fully covered per 'coverage' data, then it will add additional tests
until the coverage is 100%, by adding tests that improve the coverage.

One the limit is reached and coverage is 100%, then the decorator does not incur further overhead.

Once captured, the tests can be run using pytest unit test framework. This is particularly
useful as a check on operation between refactoring or other enhancements.

The test cases are human-readable JSON using the 'jsonpickle' package, which extends basic JSON to
also provide for capturing binary and other data that is not possible with straight JSON.
These testcase files can serve as proof of operation for any edge-tested functions.

This package consists of:

- class 'EdgeTestConfig' 
- decorator 'save_edge_tests'
- function 'apply_edge_cases'
- test runner 'test_edge.py'

## EdgeTestConfig

This class provides a means to 
- enable_edge_tests -- boolean that controls if tests will be collected from decorated functions.
- test_cases_folder -- the location where test cases will be written.
- establish functions for loading and saving data to files
- test_count_limit -- set to 10, limits the number of unique tests applied.
- test_exclusion_patterns -- when comparing multi-line text output from the tests, these
             patterns are likely to be date and version information and should be excluded. So
             that tests run at a different time and produce the same data except for these date
             and time or version patterns can be compared.

## save_edge_tests

This decorator is used to wrap functions and save their inputs and outputs as test cases.
    It creates a folder as specified in the EdgeTestConfig class named 'test_cases' (or uses an existing one) to store the test cases.
    Test cases are saved as jsonpickle files in subfolders for each module and function,
        test_cases/module_name/function_name/(hex file name).json
    
Each test case is named using the md5 hash digest of the flattened input args, kwargs, and other state.

The test case is serialize using 'jsonpickle' with the goal of producing human-readble test files.
    Each test file provides the function definition, docstring, plus all the args and kwargs passed, as
    well as any other state required to be established as global state. It provides args and kwargs after
    the call, and all data returned from the function. The test file is formatted so it can be easily read
    and used as proof of operation of the function.

## Args:
- state (dict, optional): if provided, this dict provides the name of the local state to be reproduced.
            save_edge_tests will fill in the value of the key provided with the value present when the function is called.
- function: The decorated function (provided by decoration).
- save_specs: 
        save_specs_dod (dods, optional): if provided, use alternative specs for saving/restoring data.
            save_specs_dod should have the following structure:
        
                {(arg):{'arg':(arg),'fmt':(fmt),'rtype':(fmt)}}
                
            where:
                (arg) - the name of the argument, like 'image'
                (fmt) - the desired format of the file to be saved, like '.png'
                        generally, the extension including the dot.
                (rtype) - the desired return type when the saved data is read back in during testing,
                        such as 'image', 'daf', 'df' etc.

## Returns:
Creates test data at edge_test_cases/{module}/{function_name}/{hexdigest based on inputs}.json
    
### Example:

        @edge_test_utils.save_edge_tests()
        def my_function(arg1, arg2):
            return arg1 + arg2

        # This will save edge test cases for 'my_function' in the 'test_cases' folder in subfolder 'my_function'.
        
### if external globals are used, the state must be established. 

For example, args.argsdict is used inside the function, this state must be established.
        
        @edge_test_utils.save_edge_tests(state={'args.argsdict': None})
        def my_function(arg1, arg2):
            return arg1 + arg2 + args.argsdict['value']
            
            
## apply_test_cases()

This function applies all the test cases that exist within the pytest unit-test framework.
It currently runs all the edge tests as a single test.

TODO: create generator that provides one test at a time and run each test separately.

Note: Test runner provides more extensive comparison of returned values to locate the differences.
pytest does not provide this level of detail (that I know of).

# Best Practices

To effectively use the edgetest approach:
- your functions should be pure functions
    - it is allowed to mutate passed data objects that are provided as references.
    - There should be no references to global data
        - If there are, then it must be established using the 'state' parameter.
    - no files should be read or written inside the function. If your functions include opening and saving files, then you should refactor just the core of your processing into a pure function that can be successfully decorated.
- The functions should be deterministic, i.e. no random values that are not repeatable
- Avoid positional arguments and use keyword arguments so that they argument names will be provided in the test case.

Enjoy!


