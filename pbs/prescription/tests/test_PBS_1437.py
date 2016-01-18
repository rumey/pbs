#! /us/bin/env python2.7
"""
Module: test_PBS_1437.py
Package: pbs.prescription.tests
Description: Tests to cover the PBS-1437 Jira ticket
"""
from __future__ import print_function, division, unicode_literals, absolute_import
# Imports
import pytest
from django.test import Client
# Constants

# Classes

# Functions

# Tests
def test_truth():
    assert True == True

def test_base_view(rf):
    request = rf.get('/risk/context/prescription/635/')

@pytest.mark.django_db
def test_base_url(client):
    response = client.get('/risk/context/prescription/635/')
    assert response.content

if __name__ == "__main__":
    
    print("Done __main__")
