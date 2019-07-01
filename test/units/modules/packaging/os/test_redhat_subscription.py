# Author: Jiri Hnidek (jhnidek@redhat.com)
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json

# from units.compat.mock import call, patch
from ansible.module_utils import basic
from ansible.modules.packaging.os import redhat_subscription

import pytest

TESTED_MODULE = redhat_subscription.__name__


@pytest.fixture
def patch_redhat_subscription(mocker):
    """
    Function used for mocking some parts of redhat_subscribtion module
    """
    mocker.patch('ansible.modules.packaging.os.redhat_subscription.RegistrationBase.REDHAT_REPO')
    mocker.patch('os.path.isfile', return_value=False)
    mocker.patch('os.unlink', return_value=True)
    mocker.patch('ansible.modules.packaging.os.redhat_subscription.AnsibleModule.get_bin_path',
                 return_value='/testbin/subscription-manager')


@pytest.mark.parametrize('patch_ansible_module', [{}], indirect=['patch_ansible_module'])
@pytest.mark.usefixtures('patch_ansible_module')
def test_without_required_parameters(capfd, patch_redhat_subscription):
    """
    Failure must occurs when all parameters are missing
    """
    with pytest.raises(SystemExit):
        redhat_subscription.main()
    out, err = capfd.readouterr()
    results = json.loads(out)
    assert results['failed']
    assert 'state is present but any of the following are missing' in results['msg']


TEST_CASES = [
    # Test the case, when the system is already registered
    [
        {
            'state': 'present',
            'server_hostname': 'subscription.rhsm.redhat.com',
            'username': 'admin',
            'password': 'admin',
            'org_id': 'admin'
        },
        {
            'id': 'test_already_registered_system',
            'run_command.calls': [
                (
                    # Calling of following command will be asserted
                    ['/testbin/subscription-manager', 'identity'],
                    # Was return code checked?
                    {'check_rc': False},
                    # Mock of returned code, stdout and stderr
                    (0, 'system identity: b26df632-25ed-4452-8f89-0308bfd167cb', '')
                )
            ],
            'changed': False,
            'msg': 'System already registered.'
        }
    ],
    # Test simple registration using username and password
    [
        {
            'state': 'present',
            'server_hostname': 'satellite.company.com',
            'username': 'admin',
            'password': 'admin',
        },
        {
            'id': 'test_registeration_username_password',
            'run_command.calls': [
                (
                    ['/testbin/subscription-manager', 'identity'],
                    {'check_rc': False},
                    (1, '', '')
                ),
                (
                    ['/testbin/subscription-manager', 'config', '--server.hostname=satellite.company.com'],
                    {'check_rc': True},
                    (0, '', '')
                ),
                (
                    ['/testbin/subscription-manager', 'register',
                        '--serverurl', 'satellite.company.com',
                        '--username', 'admin',
                        '--password', 'admin'],
                    {'check_rc': True, 'expand_user_and_vars': False},
                    (0, '', '')
                )
            ],
            'changed': True,
            'msg': "System successfully registered to 'satellite.company.com'."
        }
    ],
    # Test unregistration, when system is unregistered
    [
        {
            'state': 'absent',
            'server_hostname': 'subscription.rhsm.redhat.com',
            'username': 'admin',
            'password': 'admin',
        },
        {
            'id': 'test_unregisteration',
            'run_command.calls': [
                (
                    ['/testbin/subscription-manager', 'identity'],
                    {'check_rc': False},
                    (0, 'system identity: b26df632-25ed-4452-8f89-0308bfd167cb', '')
                ),
                (
                    ['/testbin/subscription-manager', 'unsubscribe', '--all'],
                    {'check_rc': True},
                    (0, '', '')
                ),
                (
                    ['/testbin/subscription-manager', 'unregister'],
                    {'check_rc': True},
                    (0, '', '')
                )
            ],
            'changed': True,
            'msg': "System successfully unregistered from subscription.rhsm.redhat.com."
        }
    ],
    # Test unregistration of already unregistered system
    [
        {
            'state': 'absent',
            'server_hostname': 'subscription.rhsm.redhat.com',
            'username': 'admin',
            'password': 'admin',
        },
        {
            'id': 'test_unregisteration_of_unregistered_system',
            'run_command.calls': [
                (
                    ['/testbin/subscription-manager', 'identity'],
                    {'check_rc': False},
                    (1, 'This system is not yet registered.', '')
                )
            ],
            'changed': False,
            'msg': "System already unregistered."
        }
    ],
    # Test registration using activation key
    [
        {
            'state': 'present',
            'server_hostname': 'satellite.company.com',
            'activationkey': 'some-activation-key',
            'org_id': 'admin'
        },
        {
            'id': 'test_registeration_activation_key',
            'run_command.calls': [
                (
                    ['/testbin/subscription-manager', 'identity'],
                    {'check_rc': False},
                    (1, 'This system is not yet registered.', '')
                ),
                (
                    ['/testbin/subscription-manager', 'config', '--server.hostname=satellite.company.com'],
                    {'check_rc': True},
                    (0, '', '')
                ),
                (
                    [
                        '/testbin/subscription-manager',
                        'register',
                        '--serverurl', 'satellite.company.com',
                        '--org', 'admin',
                        '--activationkey', 'some-activation-key'
                    ],
                    {'check_rc': True, 'expand_user_and_vars': False},
                    (0, '', '')
                )
            ],
            'changed': True,
            'msg': "System successfully registered to 'satellite.company.com'."
        }
    ]
]

TEST_CASES_IDS = [item[1]['id'] for item in TEST_CASES]


@pytest.mark.parametrize('patch_ansible_module, testcase', TEST_CASES, ids=TEST_CASES_IDS, indirect=['patch_ansible_module'])
@pytest.mark.usefixtures('patch_ansible_module')
def test_redhat_subscribtion(mocker, capfd, patch_redhat_subscription, testcase):
    """
    Run unit tests for test cases listen in TEST_CASES
    """

    # Mock function used for running commands first
    call_results = [item[2] for item in testcase['run_command.calls']]
    mock_run_command = mocker.patch.object(
        basic.AnsibleModule,
        'run_command',
        side_effect=call_results)

    # Try to run test case
    with pytest.raises(SystemExit):
        redhat_subscription.main()

    out, err = capfd.readouterr()
    results = json.loads(out)

    assert 'changed' in results
    assert results['changed'] == testcase['changed']
    assert results['msg'] == testcase['msg']

    assert basic.AnsibleModule.run_command.call_count == len(testcase['run_command.calls'])
    if basic.AnsibleModule.run_command.call_count:
        call_args_list = [(item[0][0], item[1]) for item in basic.AnsibleModule.run_command.call_args_list]
        expected_call_args_list = [(item[0], item[1]) for item in testcase['run_command.calls']]
        assert call_args_list == expected_call_args_list
