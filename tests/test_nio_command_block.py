from unittest.mock import MagicMock, patch
from requests import Response
from collections import OrderedDict

from nio.signal.base import Signal
from nio.testing.block_test_case import NIOBlockTestCase

from ..nio_command_block import NioCommand, OAuth2Exception, SecurityMethod


class TestNioCommandBlock(NIOBlockTestCase):

    @patch('requests.get')
    def test_process_signals(self, mock_get):
        access_token = 'asdf1234'
        url = 'http://127.0.0.1:8181/nio'
        headers = {}
        block = NioCommand()
        block.get_access_token = MagicMock(return_value=access_token)
        block._get_url = MagicMock(return_value=(url, headers))
        mock_get.return_value = Response()
        mock_get.return_value.status_code = 200
        mock_get.return_value.json = MagicMock()
        mock_get.return_value.json.return_value = {'asdf': 'qwer'}
        # call to init_access_token is in configure
        self.configure_block(block, {})
        block.process_signals([Signal()])
        self.assert_num_signals_notified(1, block)

    def test_init_access_token(self):
        access_token = 'asdf1234'
        block = NioCommand()
        block.get_access_token = MagicMock(return_value=access_token)
        # call to init_access_token is in configure
        self.configure_block(block, {'security_method': SecurityMethod.OAUTH})
        self.assertEqual(block._access_token, access_token)
        self.assertTrue(block._reauth_job is not None)

    def test_init_access_token_fail(self):
        block = NioCommand()
        block.get_access_token = MagicMock(side_effect=OAuth2Exception())
        # call to init_access_token is in configure
        self.configure_block(block, {})
        self.assertEqual(block._access_token, None)
        self.assertTrue(block._reauth_job is None)

    def test_get_url(self):
        command = 'start'
        service = 'service'
        block_name = 'block'
        host = '127.0.0.1'
        port = 8181
        # first test with no block
        block = NioCommand()
        self.configure_block(block, {'command_name': command,
                                     'service_name': service,
                                     'host': host,
                                     'port': port,
                                     'security_method': SecurityMethod.NONE})
        url, headers = block._get_url(Signal())
        test_url = 'http://{}:{}/services/{}/{}?'.format(
            host, port, service, command)
        self.assertEqual(url, test_url)
        self.assertDictEqual(headers, {'Content-Type': 'application/json'})
        # then test with a block
        block = NioCommand()
        self.configure_block(block, {'command_name': command,
                                     'service_name': service,
                                     'block_name': block_name,
                                     'host': '127.0.0.1',
                                     'port': 8181,
                                     'security_method': SecurityMethod.NONE})
        url, headers = block._get_url(Signal())
        test_url = 'http://{}:{}/services/{}/{}/{}?'.format(
            host, port, service, block_name, command)
        self.assertEqual(url, test_url)
        self.assertDictEqual(headers, {'Content-Type': 'application/json'})
        # and test with params
        block = NioCommand()
        self.configure_block(block, {'command_name': command,
                                     'service_name': service,
                                     'block_name': block_name,
                                     'host': '127.0.0.1',
                                     'port': 8181,
                                     'security_method': SecurityMethod.NONE})
        params = OrderedDict()
        params['p1'] = 'v1'
        params['p2'] = 'v2'
        block._get_params = MagicMock(return_value=params)
        url, headers = block._get_url(Signal())
        test_url = 'http://{}:{}/services/{}/{}/{}?p1=v1&p2=v2'.format(
            host, port, service, block_name, command)
        self.assertEqual(url, test_url)
        self.assertDictEqual(headers, {'Content-Type': 'application/json'})

    def test_get_url_fail(self):
        command = 'start'
        service = 'service'
        # first test with a command but no service.
        block = NioCommand()
        self.configure_block(block, {'command_name': command})
        url, headers = block._get_url(Signal())
        self.assertEqual(url, None)
        self.assertEqual(headers, None)
        # then test with a service but no command
        block = NioCommand()
        self.configure_block(block, {'service_name': service})
        url, headers = block._get_url(Signal())
        self.assertEqual(url, None)
        self.assertEqual(headers, None)

    def test_get_headers(self):
        block = NioCommand()
        # test with no auth
        self.configure_block(block, {'security_method': SecurityMethod.NONE})
        headers = block._get_headers()
        self.assertTrue('Authorization' not in headers)
        # test with basic auth
        self.configure_block(block,
                             {'security_method': SecurityMethod.BASIC,
                              'basic_auth_creds': {'username': 'Admin',
                                                   'password': 'Admin'}})
        headers = block._get_headers()
        self.assertEqual(headers['Authorization'], 'Basic QWRtaW46QWRtaW4=')
        # test with oauth
        block._init_access_token = MagicMock()
        block._oauth_token = {'access_token': 'asdf1234'}
        block._access_token = 'asdf1234'
        self.configure_block(block, {'security_method': SecurityMethod.OAUTH})
        headers = block._get_headers()
        self.assertEqual(headers['Authorization'],
                         'Bearer {}'.format(block._access_token))

    def test_process_response(self):
        block = NioCommand()
        block._init_access_token = MagicMock()
        self.configure_block(block, {})
        from requests import Response
        resp = Response()
        resp.status_code = 200
        resp.json = MagicMock(return_value={'asdf': 'qwer'})
        sigs = block._process_response(resp)
        self.assertEqual(sigs[0].asdf, 'qwer')

    def test_params(self):
        block = NioCommand()
        block._init_access_token = MagicMock()
        self.configure_block(block, {
            "params": [
                {
                    "prop_name": "param1",
                    "prop_value": "value1"
                },
                {
                    "prop_name": "param2",
                    "prop_value": "value2"
                }
            ]
        })

        params = block._get_params(Signal())
        self.assertEqual(params['param1'], 'value1')
        self.assertEqual(params['param2'], 'value2')

