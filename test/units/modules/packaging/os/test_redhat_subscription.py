# Author: Jiri Hnidek (jhnidek@redhat.com)
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from units.compat.mock import call, patch
from ansible.modules.packaging.os import redhat_subscription

from units.modules.utils import (AnsibleExitJson, ModuleTestCase, set_module_args)


class RedHatSubscriptionModuleTestCase(ModuleTestCase):
    module = redhat_subscription

    def setUp(self):
        super(RedHatSubscriptionModuleTestCase, self).setUp()

        # Mainly interested that the subscription-manager calls are right
        # based on the module args, so patch out run_command in the module.
        # returns (rc, out, err) structure
        self.mock_run_command = patch('ansible.modules.packaging.os.redhat_subscription.'
                                      'AnsibleModule.run_command')
        self.module_main_command = self.mock_run_command.start()

        # Module does a get_bin_path check before every run_command call
        self.mock_get_bin_path = patch('ansible.modules.packaging.os.redhat_subscription.'
                                       'AnsibleModule.get_bin_path')
        self.get_bin_path = self.mock_get_bin_path.start()
        self.get_bin_path.return_value = '/testbin/subscription-manager'

        self.mock_redhat_repo = patch('ansible.modules.packaging.os.redhat_subscription.RegistrationBase.REDHAT_REPO')
        self.redhat_repo = self.mock_redhat_repo.start()

        self.mock_is_file = patch('os.path.isfile', return_value=False)
        self.is_file = self.mock_is_file.start()

        self.mock_unlink = patch('os.unlink', return_value=True)
        self.unlink = self.mock_unlink.start()

    def tearDown(self):
        self.mock_run_command.stop()
        self.mock_get_bin_path.stop()
        super(RedHatSubscriptionModuleTestCase, self).tearDown()

    def module_main(self, exit_exc):
        with self.assertRaises(exit_exc) as exc:
            self.module.main()
        return exc.exception.args[0]

    def test_already_registered_system(self):
        """
        Test what happens, when the system is already registered
        """
        set_module_args(
            {
                'state': 'present',
                'server_hostname': 'subscription.rhsm.redhat.com',
                'username': 'admin',
                'password': 'admin',
                'org_id': 'admin'
            })
        self.module_main_command.side_effect = [
            # first call "identity" returns 0. It means that system is regisetred.
            (0, '', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertFalse(result['changed'])
        self.module_main_command.assert_has_calls([
            call(['/testbin/subscription-manager', 'identity'], check_rc=False),
        ])

    def test_registeration_username_password(self):
        """
        Test of registration using username and password
        """
        set_module_args(
            {
                'state': 'present',
                'username': 'admin',
                'password': 'admin',
                'org_id': 'admin'
            })
        self.module_main_command.side_effect = [
            # First call: "identity" returns 1. It means that system is not registered.
            (1, 'This system is not yet registered.', ''),
            # Second call: "register"
            (0, '', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])
        self.module_main_command.assert_has_calls([
            call(
                [
                    '/testbin/subscription-manager',
                    'identity'
                ], check_rc=False),
            call(
                [
                    '/testbin/subscription-manager',
                    'register',
                    '--org', 'admin',
                    '--username', 'admin',
                    '--password', 'admin'
                ], check_rc=True, expand_user_and_vars=False)
        ])

    def test_unregisteration(self):
        """
        Test of unregistration, when the system is registered
        """
        set_module_args(
            {
                'state': 'absent'
            })
        self.module_main_command.side_effect = [
            # First call: "identity" returns 0. It means that system is registered.
            (0, 'system identity: b26df632-25ed-4452-8f89-0308bfd167cb', ''),
            # Second call: "unsubscribe" returns 0.
            (0, 'System has been unregistered.', ''),
            # Third call: "unregister" returns 0.
            (0, 'System has been unregistered.', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])
        self.module_main_command.assert_has_calls([
            call(
                [
                    '/testbin/subscription-manager',
                    'identity'
                ], check_rc=False),
            call(
                [
                    '/testbin/subscription-manager',
                    'unsubscribe', '--all'
                ], check_rc=True),
            call(
                [
                    '/testbin/subscription-manager',
                    'unregister'
                ], check_rc=True)
        ])

    def test_unregisteration_of_unregistered_system(self):
        """
        Test of unregistration, when the system is already unregistered
        """
        set_module_args(
            {
                'state': 'absent'
            })
        self.module_main_command.side_effect = [
            # First call: "identity" returns 0. It means that system is registered.
            (1, 'This system is not yet registered.', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertFalse(result['changed'])
        self.module_main_command.assert_has_calls([
            call(
                [
                    '/testbin/subscription-manager',
                    'identity'
                ], check_rc=False)
        ])

    def test_registeration_username_password_satellite(self):
        """
        Test of registration using username and password against Satellite server
        """
        set_module_args(
            {
                'state': 'present',
                'server_hostname': 'satellite.company.com',
                'username': 'admin',
                'password': 'admin',
                'org_id': 'admin'
            })
        self.module_main_command.side_effect = [
            # First call: "identity" returns 1. It means that system is not registered.
            (1, 'This system is not yet registered.', ''),
            # Second call: "config" server hostname
            (0, '', ''),
            # Third call: "register"
            (0, '', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])
        self.module_main_command.assert_has_calls([
            call(
                [
                    '/testbin/subscription-manager',
                    'identity'
                ], check_rc=False),
            call(
                [
                    '/testbin/subscription-manager',
                    'config',
                    '--server.hostname=satellite.company.com'
                ], check_rc=True),
            call(
                [
                    '/testbin/subscription-manager',
                    'register',
                    '--serverurl', 'satellite.company.com',
                    '--org', 'admin',
                    '--username', 'admin',
                    '--password', 'admin'
                ], check_rc=True, expand_user_and_vars=False)
        ])

    def test_registeration_activation_key(self):
        """
        Test registration using username and password
        """
        set_module_args(
            {
                'state': 'present',
                'activationkey': 'some-activation-key',
                'org_id': 'admin'
            })
        self.module_main_command.side_effect = [
            # First call: "identity" returns 1. It means that system is not registered.
            (1, 'This system is not yet registered.', ''),
            # Second call: "config" server hostname
            (0, '', ''),
            # Third call: "register"
            (0, '', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])

        self.module_main_command.assert_has_calls([
            call(
                [
                    '/testbin/subscription-manager',
                    'identity'
                ], check_rc=False),
            call(
                [
                    '/testbin/subscription-manager',
                    'register',
                    '--org', 'admin',
                    '--activationkey', 'some-activation-key',
                ], check_rc=True, expand_user_and_vars=False)
        ])

    def test_registeration_username_password_auto_attach(self):
        """
        Test of registration using username and password with auto-attach option
        """
        set_module_args(
            {
                'state': 'present',
                'username': 'admin',
                'password': 'admin',
                'org_id': 'admin',
                'auto_attach': 'true'
            })
        self.module_main_command.side_effect = [
            # First call: "identity" returns 1. It means that system is not registered.
            (1, 'This system is not yet registered.', ''),
            # Second call: "register"
            (0, '', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])
        self.module_main_command.assert_has_calls([
            call(
                [
                    '/testbin/subscription-manager',
                    'identity'
                ], check_rc=False),
            call(
                [
                    '/testbin/subscription-manager',
                    'register',
                    '--org', 'admin',
                    '--auto-attach',
                    '--username', 'admin',
                    '--password', 'admin'
                ], check_rc=True, expand_user_and_vars=False)
        ])

    def test_force_registeration_username_password(self):
        """
        Test of force registration despite the system is already registered
        """
        set_module_args(
            {
                'state': 'present',
                'username': 'admin',
                'password': 'admin',
                'org_id': 'admin',
                'force_register': 'true'
            })
        self.module_main_command.side_effect = [
            # First call: "identity" returns 0. It means that system is not registered.
            (0, 'This system already registered.', ''),
            # Third call: "register"
            (0, '', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])
        self.module_main_command.assert_has_calls([
            call(
                [
                    '/testbin/subscription-manager',
                    'identity'
                ], check_rc=False),
            call(
                [
                    '/testbin/subscription-manager',
                    'register',
                    '--force',
                    '--org', 'admin',
                    '--username', 'admin',
                    '--password', 'admin'
                ], check_rc=True, expand_user_and_vars=False)
        ])

    def test_registeration_username_password_proxy_options(self):
        """
        Test of registration using username, password and proxy options
        """
        set_module_args(
            {
                'state': 'present',
                'username': 'admin',
                'password': 'admin',
                'org_id': 'admin',
                'server_proxy_hostname': 'proxy.company.com',
                'server_proxy_port': '12345',
                'server_proxy_user': 'proxy_user',
                'server_proxy_password': 'secret_proxy_password'
            })
        self.module_main_command.side_effect = [
            # First call: "identity" returns 1. It means that system is not registered.
            (1, 'This system is not yet registered.', ''),
            # Second call: "config"
            (0, '', ''),
            # Third call: "register"
            (0, '', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])
        self.module_main_command.assert_has_calls([
            call(
                [
                    '/testbin/subscription-manager',
                    'identity'
                ], check_rc=False),
            call(
                [
                    '/testbin/subscription-manager',
                    'config',
                    '--server.proxy_hostname=proxy.company.com',
                    '--server.proxy_password=secret_proxy_password',
                    '--server.proxy_port=12345',
                    '--server.proxy_user=proxy_user'], check_rc=True),
            call(
                [
                    '/testbin/subscription-manager',
                    'register',
                    '--org', 'admin',
                    '--proxy', 'proxy.company.com:12345',
                    '--proxyuser', 'proxy_user',
                    '--proxypassword', 'secret_proxy_password',
                    '--username', 'admin',
                    '--password', 'admin'
                ], check_rc=True, expand_user_and_vars=False)
        ])

    def test_registeration_username_password_pool(self):
        """
        Test of registration using username and password and attach to pool
        """
        set_module_args(
            {
                'state': 'present',
                'username': 'admin',
                'password': 'admin',
                'org_id': 'admin',
                'pool': 'ff8080816b8e967f016b8e99632804a6'
            })
        self.module_main_command.side_effect = [
            # First call: "identity" returns 1. It means that system is not registered.
            (1, 'This system is not yet registered.', ''),
            # Second call: "register"
            (0, '', ''),
            # Third call: "list --available"
            (
                0,
                '''
+-------------------------------------------+
    Available Subscriptions
+-------------------------------------------+
Subscription Name:   SP Server Premium (S: Premium, U: Production, R: SP Server)
Provides:            SP Server Bits
SKU:                 sp-server-prem-prod
Contract:            0
Pool ID:             ff8080816b8e967f016b8e99632804a6
Provides Management: Yes
Available:           5
Suggested:           1
Service Type:        L1-L3
Roles:               SP Server
Service Level:       Premium
Usage:               Production
Add-ons:
Subscription Type:   Standard
Starts:              06/25/19
Ends:                06/24/20
Entitlement Type:    Physical
                ''', ''),
            # 4th call: "attach --pool ff8080816b8e967f016b8e99632804a6"
            (0, '', ''),
            (0, '', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])
        self.module_main_command.assert_has_calls([
            call(
                [
                    '/testbin/subscription-manager',
                    'identity'
                ], check_rc=False),
            call(
                [
                    '/testbin/subscription-manager',
                    'register',
                    '--org', 'admin',
                    '--username', 'admin',
                    '--password', 'admin'
                ], check_rc=True, expand_user_and_vars=False),
            call('subscription-manager list --available', check_rc=True,
                 environ_update={'LANG': 'C', 'LC_ALL': 'C', 'LC_MESSAGES': 'C'}),
            call('subscription-manager attach --pool ff8080816b8e967f016b8e99632804a6',
                 check_rc=True)
        ])

    def test_registeration_username_password_pool_ids_quantities(self):
        """
        Test of registration using username and password and attach to pool ID and quantities
        """
        set_module_args(
            {
                'state': 'present',
                'username': 'admin',
                'password': 'admin',
                'org_id': 'admin',
                'pool_ids': [{'ff8080816b8e967f016b8e99632804a6': 2}, {'ff8080816b8e967f016b8e99747107e9': 4}]
            })
        self.module_main_command.side_effect = [
            # First call: "identity" returns 1. It means that system is not registered.
            (1, 'This system is not yet registered.', ''),
            # Second call: "register"
            (0, '', ''),
            # Third call: "list --available"
            (
                0,
                '''
+-------------------------------------------+
    Available Subscriptions
+-------------------------------------------+
Subscription Name:   SP Smart Management (A: ADDON1)
Provides:            SP Addon 1 bits
SKU:                 sp-with-addon-1
Contract:            1
Pool ID:             ff8080816b8e967f016b8e99747107e9
Provides Management: Yes
Available:           10
Suggested:           1
Service Type:
Roles:
Service Level:
Usage:
Add-ons:             ADDON1
Subscription Type:   Standard
Starts:              25.6.2019
Ends:                24.6.2020
Entitlement Type:    Physical

Subscription Name:   SP Server Premium (S: Premium, U: Production, R: SP Server)
Provides:            SP Server Bits
SKU:                 sp-server-prem-prod
Contract:            0
Pool ID:             ff8080816b8e967f016b8e99632804a6
Provides Management: Yes
Available:           5
Suggested:           1
Service Type:        L1-L3
Roles:               SP Server
Service Level:       Premium
Usage:               Production
Add-ons:
Subscription Type:   Standard
Starts:              06/25/19
Ends:                06/24/20
Entitlement Type:    Physical
                ''', ''),
            # 4th call: "attach --pool ff8080816b8e967f016b8e99632804a6"
            (0, '', ''),
            (0, '', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])
        self.module_main_command.assert_has_calls([
            call(
                [
                    '/testbin/subscription-manager',
                    'identity'
                ], check_rc=False),
            call(
                [
                    '/testbin/subscription-manager',
                    'register',
                    '--org', 'admin',
                    '--username', 'admin',
                    '--password', 'admin'
                ], check_rc=True, expand_user_and_vars=False),
            call('subscription-manager list --available', check_rc=True,
                 environ_update={'LANG': 'C', 'LC_ALL': 'C', 'LC_MESSAGES': 'C'}),
            call(
                [
                    '/testbin/subscription-manager',
                    'attach',
                    '--pool', 'ff8080816b8e967f016b8e99632804a6',
                    '--quantity', '2'
                ], check_rc=True),
            call(
                [
                    '/testbin/subscription-manager',
                    'attach',
                    '--pool', 'ff8080816b8e967f016b8e99747107e9',
                    '--quantity', '4'
                ], check_rc=True)
        ])

    def test_registeration_username_password_pool_ids(self):
        """
        Test of registration using username and password and attach to pool ID without quantities
        """
        set_module_args(
            {
                'state': 'present',
                'username': 'admin',
                'password': 'admin',
                'org_id': 'admin',
                'pool_ids': ['ff8080816b8e967f016b8e99632804a6', 'ff8080816b8e967f016b8e99747107e9']
            })
        self.module_main_command.side_effect = [
            # First call: "identity" returns 1. It means that system is not registered.
            (1, 'This system is not yet registered.', ''),
            # Second call: "register"
            (0, '', ''),
            # Third call: "list --available"
            (
                0,
                '''
+-------------------------------------------+
    Available Subscriptions
+-------------------------------------------+
Subscription Name:   SP Smart Management (A: ADDON1)
Provides:            SP Addon 1 bits
SKU:                 sp-with-addon-1
Contract:            1
Pool ID:             ff8080816b8e967f016b8e99747107e9
Provides Management: Yes
Available:           10
Suggested:           1
Service Type:
Roles:
Service Level:
Usage:
Add-ons:             ADDON1
Subscription Type:   Standard
Starts:              25.6.2019
Ends:                24.6.2020
Entitlement Type:    Physical

Subscription Name:   SP Server Premium (S: Premium, U: Production, R: SP Server)
Provides:            SP Server Bits
SKU:                 sp-server-prem-prod
Contract:            0
Pool ID:             ff8080816b8e967f016b8e99632804a6
Provides Management: Yes
Available:           5
Suggested:           1
Service Type:        L1-L3
Roles:               SP Server
Service Level:       Premium
Usage:               Production
Add-ons:
Subscription Type:   Standard
Starts:              06/25/19
Ends:                06/24/20
Entitlement Type:    Physical
                ''', ''),
            # 4th call: "attach --pool ff8080816b8e967f016b8e99632804a6"
            (0, '', ''),
            (0, '', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])
        self.module_main_command.assert_has_calls([
            call(
                [
                    '/testbin/subscription-manager',
                    'identity'
                ], check_rc=False),
            call(
                [
                    '/testbin/subscription-manager',
                    'register',
                    '--org', 'admin',
                    '--username', 'admin',
                    '--password', 'admin'
                ], check_rc=True, expand_user_and_vars=False),
            call('subscription-manager list --available', check_rc=True,
                 environ_update={'LANG': 'C', 'LC_ALL': 'C', 'LC_MESSAGES': 'C'}),
            call(
                [
                    '/testbin/subscription-manager',
                    'attach',
                    '--pool', 'ff8080816b8e967f016b8e99632804a6',
                    '--quantity', '1'
                ], check_rc=True),
            call(
                [
                    '/testbin/subscription-manager',
                    'attach',
                    '--pool', 'ff8080816b8e967f016b8e99747107e9',
                    '--quantity', '1'
                ], check_rc=True)
        ])

    def test_registeration_username_password_pool_id(self):
        """
        Test of registration using username and password and attach to pool ID (one pool)
        """
        set_module_args(
            {
                'state': 'present',
                'username': 'admin',
                'password': 'admin',
                'org_id': 'admin',
                'pool_ids': 'ff8080816b8e967f016b8e99632804a6'
            })
        self.module_main_command.side_effect = [
            # First call: "identity" returns 1. It means that system is not registered.
            (1, 'This system is not yet registered.', ''),
            # Second call: "register"
            (0, '', ''),
            # Third call: "list --available"
            (
                0,
                '''
+-------------------------------------------+
    Available Subscriptions
+-------------------------------------------+
Subscription Name:   SP Smart Management (A: ADDON1)
Provides:            SP Addon 1 bits
SKU:                 sp-with-addon-1
Contract:            1
Pool ID:             ff8080816b8e967f016b8e99747107e9
Provides Management: Yes
Available:           10
Suggested:           1
Service Type:
Roles:
Service Level:
Usage:
Add-ons:             ADDON1
Subscription Type:   Standard
Starts:              25.6.2019
Ends:                24.6.2020
Entitlement Type:    Physical

Subscription Name:   SP Server Premium (S: Premium, U: Production, R: SP Server)
Provides:            SP Server Bits
SKU:                 sp-server-prem-prod
Contract:            0
Pool ID:             ff8080816b8e967f016b8e99632804a6
Provides Management: Yes
Available:           5
Suggested:           1
Service Type:        L1-L3
Roles:               SP Server
Service Level:       Premium
Usage:               Production
Add-ons:
Subscription Type:   Standard
Starts:              06/25/19
Ends:                06/24/20
Entitlement Type:    Physical
                ''', ''),
            # 4th call: "attach --pool ff8080816b8e967f016b8e99632804a6"
            (0, '', ''),
            (0, '', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])
        self.module_main_command.assert_has_calls([
            call(
                [
                    '/testbin/subscription-manager',
                    'identity'
                ], check_rc=False),
            call(
                [
                    '/testbin/subscription-manager',
                    'register',
                    '--org', 'admin',
                    '--username', 'admin',
                    '--password', 'admin'
                ], check_rc=True, expand_user_and_vars=False),
            call('subscription-manager list --available', check_rc=True,
                 environ_update={'LANG': 'C', 'LC_ALL': 'C', 'LC_MESSAGES': 'C'}),
            call(
                [
                    '/testbin/subscription-manager',
                    'attach',
                    '--pool', 'ff8080816b8e967f016b8e99632804a6',
                    '--quantity', '1'
                ], check_rc=True),
        ])

    def test_attaching_different_pool_ids(self):
        """
        Test attaching different set of pool IDs
        """
        set_module_args(
            {
                'state': 'present',
                'username': 'admin',
                'password': 'admin',
                'org_id': 'admin',
                'pool_ids': [{'ff8080816b8e967f016b8e99632804a6': 2}, {'ff8080816b8e967f016b8e99747107e9': 4}]
            })
        self.module_main_command.side_effect = [
            # First call: "identity" returns 0. It means that system is already registered.
            (0, 'system identity: b26df632-25ed-4452-8f89-0308bfd167cb', ''),
            # Second call: "list --consumed"
            (
                0,
                '''
+-------------------------------------------+
   Consumed Subscriptions
+-------------------------------------------+
Subscription Name:   Multi-Attribute Stackable (4 cores, no content)
Provides:            Multi-Attribute Limited Product (no content)
SKU:                 cores4-multiattr
Contract:            1
Account:             12331131231
Serial:              7807912223970164816
Pool ID:             ff8080816b8e967f016b8e995f5103b5
Provides Management: No
Active:              True
Quantity Used:       1
Service Type:        Level 3
Roles:
Service Level:       Premium
Usage:
Add-ons:
Status Details:      Subscription is current
Subscription Type:   Stackable
Starts:              06/25/19
Ends:                06/24/20
Entitlement Type:    Physical
                ''',
                ''
            ),
            # Third call: "unsibscribe"
            (0, '', ''),
            # 4th call: "list --available"
            (
                0,
                '''
+-------------------------------------------+
    Available Subscriptions
+-------------------------------------------+
Subscription Name:   SP Smart Management (A: ADDON1)
Provides:            SP Addon 1 bits
SKU:                 sp-with-addon-1
Contract:            1
Pool ID:             ff8080816b8e967f016b8e99747107e9
Provides Management: Yes
Available:           10
Suggested:           1
Service Type:
Roles:
Service Level:
Usage:
Add-ons:             ADDON1
Subscription Type:   Standard
Starts:              25.6.2019
Ends:                24.6.2020
Entitlement Type:    Physical

Subscription Name:   SP Server Premium (S: Premium, U: Production, R: SP Server)
Provides:            SP Server Bits
SKU:                 sp-server-prem-prod
Contract:            0
Pool ID:             ff8080816b8e967f016b8e99632804a6
Provides Management: Yes
Available:           5
Suggested:           1
Service Type:        L1-L3
Roles:               SP Server
Service Level:       Premium
Usage:               Production
Add-ons:
Subscription Type:   Standard
Starts:              06/25/19
Ends:                06/24/20
Entitlement Type:    Physical
                ''',
                ''),
            # 4th call: "attach --pool ff8080816b8e967f016b8e99632804a6"
            (0, '', ''),
            (0, '', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])
        self.module_main_command.assert_has_calls([
            call(
                [
                    '/testbin/subscription-manager',
                    'identity'
                ], check_rc=False),
            call('subscription-manager list --consumed', check_rc=True,
                 environ_update={'LANG': 'C', 'LC_ALL': 'C', 'LC_MESSAGES': 'C'}),
            call(['/testbin/subscription-manager', 'unsubscribe', '--serial=7807912223970164816'],
                 check_rc=True),
            call('subscription-manager list --available', check_rc=True,
                 environ_update={'LANG': 'C', 'LC_ALL': 'C', 'LC_MESSAGES': 'C'}),
            call(
                [
                    '/testbin/subscription-manager',
                    'attach',
                    '--pool', 'ff8080816b8e967f016b8e99632804a6',
                    '--quantity', '2'
                ], check_rc=True),
            call(
                [
                    '/testbin/subscription-manager',
                    'attach',
                    '--pool', 'ff8080816b8e967f016b8e99747107e9',
                    '--quantity', '4'
                ], check_rc=True)
        ])
