import mock
from ckan.lib.cli import MockTranslator


def setup():
    # Register a mock translator instead of having ckan domain translations defined
    patcher = mock.patch('pylons.i18n.translation._get_translator', return_value=MockTranslator())
    patcher.start()


def teardown():
    mock.patch.stopall()
