# edgetest

This package provides utilities and tools to implement edge testing of python functions/methods.

Note: This has been recently split from another repo and may need some adjustments for general-purpose
use.

Essentially, it creates test data during actual operation of your code. 
Test data is collected only for unique input parameters of the code, up to the limit established.
If the function is not fully covered per 'coverage' data, then it will add additional tests
until the coverage is 100%, by adding tests that improve the coverage.

Once captured, the tests can be run using pytest unit test framework. This is particularly
useful as a check on operation between refactoring or other enhancements.

The test cases are human-readable JSON with the possibility that some fields are pickled. If they 
are pickled, then the __str__ or __repr__ version of the object is provided. These files can serve
as proof of operation for any edge-tested functions.

It consists of:

- decorator 'save_edge_tests'
- function 'apply_edge_cases'
- test runner 'test_edge.py'

## save_edge_tests

This decorator is used to wrap functions and save their inputs and outputs as test cases.
    It creates a folder named 'test_cases' (or uses an existing one) to store the test cases.
    Test cases are saved as pickle files in subfolders named after the function they belong to.
    Each test case file contains the module name, function name, inputs, and outputs.
    
Each test case is named using the md4 hash digest of the flattened input args, kwargs, and other state.

The test case is serialize using 'jsonpickle' with the goal of producing human-readble test files.
    Each test file provides the function definition, docstring, plus all the args and kwargs passed, as
    well as any other state required to be established as global state. It provides args and kwargs after
    the call, and all data returned from the function. The test file is formatted so it can be easily read
    and used as proof of operation of the function.

The class EdgeTestConfig provides settings to control the operation of the decorator.
         
- test_count_limit -- set to 10, limits the number of unique tests applied.
- test_exclusion_patterns -- when comparing multi-line text output from the tests, these
             patterns are likely to be date and version information and should be excluded. So
             that tests run at a different time and produce the same data except for these date
             and time or version patterns can be compared.
- enable_edge_tests -- boolean that controls if tests will be collected from decorated functions.
- test_cases_folder -- the location where test cases will be written.

## Args:
- state (dict, optional): if provided, this dict provides the name of the local state to be reproduced.
            save_edge_tests will fill in the value of the key provided with the value present when the function is called.
- function: The decorated function (provided by decoration).

## Returns:
Creates test data at edge_test_cases/{module}/{function_name}/{hexdigest based on inputs}.json
    
### Example:

        @edge_test_utils.save_edge_tests()
        def my_function(arg1, arg2):
            return arg1 + arg2

        # This will save edge test cases for 'my_function' in the 'test_cases' folder in subfolder 'my_function'.
        
### if external globals are used, the state must be established. 

Here, args.argsdict is used inside the function, this state must be established.
        
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
- your functions should be pure in form, but it is allowed to mutate passed data objects that are provided as references.
- There should be no references to global data
- no files should be read or written inside the function. If your functions include opening and saving files, then you should refactor just the core of your processing into a pure function that can be successfully decorated.
- The functions should be deterministic, i.e. no random values that are not repeatable.
- Avoid positional arguments and use keyword arguments so that they argument names will be provided in the test case.

Enjoy!


