#! /us/bin/env python2.7
"""
Module: fund_allocation.py
Package: pbs.prescription
Description: Utility functions in support of the FundAllocation model and views
"""
from __future__ import print_function, division, unicode_literals, absolute_import
# Imports
import pbs
# from pbs.prescription.models import Prescription, FundingAllocation
# Constants

# Classes

# Functions
def queryset(p_pk):
    """
    Return a list of the FundingAllocation object related to a prescription.

    We must ensure that we have one of each type at most.
    """
    # Get all the allocations for the prescription
    qs = FundingAllocation.objects.filter(prescription__pk=pk)

    return qs

def context(queryset):
    """
    Build the context for the view.
    """
    pass

def harvest(post):
    """
    Filter the post data for just the funding allocation formset data.
    """
    data = {k: post[k] for k in post if k.startswith("fundingallocation")}
    return data


# Tests

if __name__ == "__main__":

    # qs = queryset(207)
    # print(qs)

    print("Done __main__")
