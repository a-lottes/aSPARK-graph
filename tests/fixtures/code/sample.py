"""A tiny fixture module exercising classes, methods, functions and imports."""

import os
from collections import OrderedDict


def top_level_function(x):
    return x + 1


class Widget:
    def __init__(self, name):
        self.name = name

    def render(self):
        return helper(self.name)


def helper(value):
    return str(value)
