#! /usr/bin/env python2.7
"""
Module     : test_dev_PBS_1551.py
Package    : pbs.prescription.tests
Description: Add multiple allocation codes
"""
from __future__ import (
    print_function, division, unicode_literals, absolute_import)

from nose.tools import *
# Imports

import logging
logging.disable(logging.CRITICAL)

# Functions
def test_truth():
    assert True == False



# Test the url

# Test the model
def test_funding_allocation_model():
    from pbs.prescription.models import FundingAllocation
    m = FundingAllocation()
    assert m

# Test the view

# Test the template

if __name__ == "__main__":

    print("Done __main__")

