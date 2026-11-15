#!/usr/bin/env python3
"""Compatibility shim: the gate now lives in gate/unswayed.py.

Hooks installed before the rename call this file by path; keep it working.
"""
import os
import runpy
import sys

if __name__ == "__main__":
    target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unswayed.py")
    sys.argv[0] = target
    runpy.run_path(target, run_name="__main__")
