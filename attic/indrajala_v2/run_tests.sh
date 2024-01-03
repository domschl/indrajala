#!/bin/bash

# Terminate script on first error.
set -e

echo "========================================================================="
echo "||                    RUST INDRAJALA SERVER TESTS                      ||"
echo "========================================================================="
cargo test

echo "========================================================================="
echo "||                   PYTHON INDRAJALA CLIENT TESTS                     ||"
echo "========================================================================="
cd python_indrajala/indralib/tests
python indra_test.py
cd ../../..

echo "========================================================================="
echo "||                   SWIFT INDRAJALA CLIENT TESTS                      ||"
echo "========================================================================="
cd swift_indrajala/indralib/Tests
swift test
cd ../../..

echo "All done!"
