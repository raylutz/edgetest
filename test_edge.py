# test_edge.py

import sys
import unittest
from utilities import edge_test_utils

# Global parameters
#TEST_CASES_FOLDER = 'edge_test_cases'

class TestEdge(unittest.TestCase):
    """
    Unit tests for edge cases.

    This test class dynamically loads test cases from saved test case (jsonpickled) files and asserts that the 
    output of the tested functions matches the expected output. Test cases are stored in the 
    'test_cases' folder, with each function having its own subfolder containing pickle files 
    representing different test cases.

    Attributes:
        TEST_CASES_FOLDER (str): The folder path where test cases are stored.

    Methods:
        test_edge: Test function that loads and executes test cases from pickle files.

    Example:
        To run the unit tests in this class, execute 'python -m unittest test_edge.py' 
        from the command line.
    """

    def test_edge(self):
        """
        Test function that loads and executes test cases from pickle files.
        
        This method iterates through the pickle files in the 'test_cases' folder, loads each 
        test case, dynamically imports the corresponding module, and calls the function with 
        the saved inputs. It then asserts that the result matches the expected output.

        Raises:
            AssertionError: If the result of the function execution does not match the 
                expected output.
        """
        self.maxDiff = None

        edge_test_utils.apply_test_cases()
        
        
        

if __name__ == '__main__':

    args = sys.argv
    
    if len(args) > 1:
        test_case_path = sys.argv[1]
        
        edge_test_utils.apply_edge_test_at_path(test_case_path, print_details=True, break_on_error=True)
        
    else:    
        
        unittest.main()
