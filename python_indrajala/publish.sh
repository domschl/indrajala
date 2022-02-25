#!/bin/bash

rm dist/*
python -m build
twine upload dist/*

