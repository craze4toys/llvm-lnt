# Check that the LNT REST JSON API is working.
# create temporary instance
# RUN: rm -rf %t.instance
# RUN: python %{shared_inputs}/create_temp_instance.py \
# RUN:     %s %{shared_inputs}/SmallInstance \
# RUN:     %t.instance %S/Inputs/V4Pages_extra_records.sql
#
# RUN: python %s %t.instance

import logging
import sys
import unittest

import lnt.server.db.migrate
import lnt.server.ui.app
from V4Pages import check_json

logging.basicConfig(level=logging.DEBUG)

machines_expected_response = [{u'hardware': u'x86_64',
                               u'os': u'Darwin 11.3.0',
                               u'id': 1,
                               u'name': u'localhost__clang_DEV__x86_64',
                               u'uname': u'Darwin localhost 11.3.0 Darwin Kernel Version 11.3.0: Thu Jan 12'
                                         u' 18:47:41 PST 2012; root:xnu-1699.24.23~1/RELEASE_X86_64 x86_64'},
                              {u'hardware': u'AArch64',
                               u'os': u'linux',
                               u'id': 2,
                               u'name': u'machine2'},
                              {u'hardware': u'AArch64',
                               u'os': u'linux',
                               u'id': 3,
                               u'name': u'machine3'}]

order_expected_response = {u'llvm_project_revision': u'154331',
                           u'id': 1,
                           u'name': u'154331'}

graph_data = [[[152292], 1.0,
               {u'date': u'2012-05-01 16:28:23',
                u'label': u'152292',
                u'runID': u'5'}],
              [[152293], 10.0,
               {u'date': u'2012-05-03 16:28:24',
                u'label': u'152293',
                u'runID': u'6'}]]

graph_data2 = [[[152293], 10.0,
                {u'date': u'2012-05-03 16:28:24',
                 u'label': u'152293',
                 u'runID': u'6'}]]

possible_run_keys = {u'__report_version__',
                     u'inferred_run_order',
                     u'test_suite_revision',
                     u'simple_run_id',
                     u'cc_alt_src_revision',
                     u'USE_REFERENCE_OUTPUT',
                     u'cc_as_version',
                     u'DISABLE_CBE',
                     u'ENABLE_OPTIMIZED',
                     u'ARCH',
                     u'id',
                     u'DISABLE_JIT',
                     u'TARGET_CXX',
                     u'TARGET_CC',
                     u'TARGET_LLVMGXX',
                     u'cc_build',
                     u'sw_vers',
                     u'cc_src_branch',
                     u'cc1_exec_hash',
                     u'TARGET_FLAGS',
                     u'CC_UNDER_TEST_TARGET_IS_X86_64',
                     u'ENABLE_HASHED_PROGRAM_OUTPUT',
                     u'cc_name',
                     u'order_id',
                     u'start_time',
                     u'cc_version_number',
                     u'cc_alt_src_branch',
                     u'cc_version',
                     u'OPTFLAGS',
                     u'cc_ld_version',
                     u'imported_from',
                     u'TARGET_LLVMGCC',
                     u'LLI_OPTFLAGS',
                     u'cc_target',
                     u'CC_UNDER_TEST_IS_CLANG',
                     u'cc_src_revision',
                     u'end_time',
                     u'TEST',
                     u'LLC_OPTFLAGS',
                     u'machine_id',
                     u'order',
                     u'cc_exec_hash',
                     }

possible_machine_keys = {u'name',
                         u'hardware',
                         u'os',
                         u'id',
                         u'uname'}


class JSONAPITester(unittest.TestCase):
    """Test the REST api."""

    def setUp(self):
        """Bind to the LNT test instance."""
        _, instance_path = sys.argv
        app = lnt.server.ui.app.App.create_standalone(instance_path)
        app.testing = True
        self.client = app.test_client()

    def _check_response_is_wellformed(self, response):
        """API Should always return the generated by field in the top level dict."""
        # All API calls should return a top level dict.
        self.assertEqual(type(response), dict)

        # There should be no unexpected top level keys.
        all_top_level_keys = {'generated_by', 'machines', 'runs', 'orders', 'samples'}
        self.assertTrue(set(response.keys()).issubset(all_top_level_keys))
        # All API calls should return as generated by.
        self.assertIn("LNT Server v", response['generated_by'])

    def test_machine_api(self):
        """Check /machines/ and /machines/n return expected results from testdb.
        """
        client = self.client

        # All machines returns the list of machines with parameters, but no runs.
        j = check_json(client, 'api/db_default/v4/nts/machines/')
        self._check_response_is_wellformed(j)
        self.assertEquals(j['machines'], machines_expected_response)
        self.assertIsNone(j.get('runs'))

        # Machine + properties + run information.
        j = check_json(client, 'api/db_default/v4/nts/machines/1')
        self._check_response_is_wellformed(j)
        self.assertEqual(len(j['machines']), 1)
        for machine in j['machines']:
            self.assertSetEqual(set(machine.keys()), possible_machine_keys)
        expected = {"hardware": "x86_64", "os": "Darwin 11.3.0", "id": 1}
        self.assertDictContainsSubset(expected, j['machines'][0])

        self.assertEqual(len(j['runs']), 2)
        self.assertSetEqual(set(j['runs'][0].keys()), possible_run_keys)

        # Invalid machine ids are 404.
        check_json(client, 'api/db_default/v4/nts/machines/99', expected_code=404)
        check_json(client, 'api/db_default/v4/nts/machines/foo', expected_code=404)

    def test_run_api(self):
        """Check /runs/n returns expected run information."""
        client = self.client
        j = check_json(client, 'api/db_default/v4/nts/runs/1')
        self._check_response_is_wellformed(j)
        expected = {"end_time": "2012-04-11T16:28:58",
                    "order_id": 1,
                    "start_time": "2012-04-11T16:28:23",
                    "machine_id": 1,
                    "id": 1,
                    "order": u'154331'}
        self.assertDictContainsSubset(expected, j['runs'][0])
        self.assertEqual(len(j['samples']), 2)
        # This should not be a run.
        check_json(client, 'api/db_default/v4/nts/runs/100', expected_code=404)

    def test_order_api(self):
        """ Check /orders/n returns the expected order information."""
        client = self.client
        j = check_json(client, 'api/db_default/v4/nts/orders/1')
        self._check_response_is_wellformed(j)
        self.assertEquals(j['orders'][0], order_expected_response)
        check_json(client, 'api/db_default/v4/nts/orders/100', expected_code=404)

    def test_graph_api(self):
        """Check that /graph/x/y/z returns what we expect."""
        client = self.client

        j = check_json(client, 'api/db_default/v4/nts/graph/2/4/3')
        # TODO: Graph API needs redesign to be well formed.
        # self._check_response_is_wellformed(j)
        self.assertEqual(graph_data, j)

        # Now check that limit works.
        j2 = check_json(client, 'api/db_default/v4/nts/graph/2/4/3?limit=1')
        # self._check_response_is_wellformed(j)
        self.assertEqual(graph_data2, j2)

    def test_samples_api(self):
        """Samples API."""
        client = self.client
        # Run IDs must be passed, so 400 if they are not.
        check_json(client, 'api/db_default/v4/nts/samples',
                   expected_code=400)

        # Simple single run.
        j = check_json(client, 'api/db_default/v4/nts/samples?runid=1')
        self._check_response_is_wellformed(j)
        expected = [
            {u'compile_time': 0.007, u'llvm_project_revision': u'154331',
             u'hash': None,
             u'name': u'SingleSource/UnitTests/2006-12-01-float_varg',
             u'run_id': 1, u'execution_time': 0.0003,
             u'mem_bytes': None, u'compile_status': None,
             u'execution_status': None, u'score': None,
             u'hash_status': None, u'code_size': None, u'id': 1},
            {u'compile_time': 0.0072, u'llvm_project_revision': u'154331',
             u'hash': None,
             u'name': u'SingleSource/UnitTests/2006-12-04-DynAllocAndRestore',
             u'run_id': 1,
             u'execution_time': 0.0003, u'mem_bytes': None,
             u'compile_status': None, u'execution_status': None,
             u'score': None, u'hash_status': None, u'code_size': None,
             u'id': 2}]

        self.assertEqual(j['samples'], expected)

        # Check that other args are ignored.
        extra_param = check_json(client,
                                 'api/db_default/v4/nts/samples?runid=1&foo=bar')
        self._check_response_is_wellformed(extra_param)
        self.assertEqual(j, extra_param)
        # There is only one run in the DB.
        two_runs = check_json(client,
                              'api/db_default/v4/nts/samples?runid=1&runid=2')
        self._check_response_is_wellformed(two_runs)
        self.assertEqual(j, two_runs)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0], ])
