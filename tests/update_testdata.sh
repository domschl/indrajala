# Since some of the sub-projects are distributed as independent packages, the test data must be made available as copy to each package.

echo "Copying mqcmp tes data to all implementations of indralib clients and servers:"
cp -v domain_test_data/mqcmp_data.json ../python_indrajala/indralib/tests/
cp -v calendar_test_data/wp_decimal_time_data.json ../python_indrajala/indralib/tests/
