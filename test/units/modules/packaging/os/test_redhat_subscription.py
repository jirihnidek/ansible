# (c) 2018, Sean Myers <sean.myers@redhat.com>
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
        self.mock_run_command = patch('ansible.modules.packaging.os.rhsm_release.'
                                      'AnsibleModule.run_command')
        self.module_main_command = self.mock_run_command.start()

        # Module does a get_bin_path check before every run_command call
        self.mock_get_bin_path = patch('ansible.modules.packaging.os.rhsm_release.'
                                       'AnsibleModule.get_bin_path')
        self.get_bin_path = self.mock_get_bin_path.start()
        self.get_bin_path.return_value = '/testbin/subscription-manager'

        mocker.patch.object(redhat_subscription.RegistrationBase, 'REDHAT_REPO')
        mock_isfile = mocker.patch('os.path.isfile', return_value=True)

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

    def test_registeration_of_system(self):
        """
        Test registration using username and password
        """
        set_module_args(
            {
                'state': 'present',
                'username': 'admin',
                'password': 'admin',
                'org_id': 'admin'
            })
        self.module_main_command.side_effect = [
            # first call "identity" returns 1. It means that system is not regisetred.
            (1, 'This system is not yet registered.', ''),
            # second call, register: just needs to exit with 0 rc
            (0, '', ''),
        ]
        # TODO: mock /etc/yum.repos.d/redhat.repo, because subscription-manager wants
        # to write to this file.

        result = self.module_main(AnsibleExitJson)

        self.assertFalse(result['changed'])
        self.module_main_command.assert_has_calls([
            call(['/testbin/subscription-manager', 'identity'], check_rc=False),
        ])
