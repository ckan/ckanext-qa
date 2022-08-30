import logging
import sys
import ckan.plugins as p
import ckanext.qa.utils as utils

REQUESTS_HEADER = {'content-type': 'application/json',
                   'User-Agent': 'ckanext-qa commands'}


class CkanApiError(Exception):
    pass


class QACommand(p.toolkit.CkanCommand):
    """
    QA analysis of CKAN resources

    Usage::

        paster qa init
           - Creates the database tables that QA expects for storing
           results

        paster qa [options] update [dataset/group name/id]
           - QA analysis on all resources in a given dataset, or on all
           datasets if no dataset given

        paster qa sniff {filepath}
           - Opens the file and determines its type by the contents

        paster qa view [dataset name/id]
           - See package score information

        paster qa clean
           - Remove all package score information

        paster qa migrate1
           - Migrates the way results are stored in task_status,
             with commit 6f63ab9e 20th March 2013
             (from key='openness_score'/'openness_score_failure_count' to
              key='status')

    The commands should be run from the ckanext-qa directory and expect
    a development.ini file to be present. Most of the time you will
    specify the config explicitly though::

        paster qa update --config=<path to CKAN config file>
    """

    summary = __doc__.split('\n')[0]
    usage = __doc__
    min_args = 0

    def __init__(self, name):
        super(QACommand, self).__init__(name)
        self.parser.add_option('-q', '--queue',
                               action='store',
                               dest='queue',
                               help='Send to a particular queue')

    def command(self):
        """
        Parse command line arguments and call appropriate method.
        """
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print(QACommand.__doc__)
            return

        cmd = self.args[0]
        self._load_config()

        # Now we can import ckan and create logger, knowing that loggers
        # won't get disabled
        self.log = logging.getLogger('ckanext.qa')

        if cmd == 'update':
            self.update()
        elif cmd == 'sniff':
            self.sniff()
        elif cmd == 'view':
            if len(self.args) == 2:
                self.view(self.args[1])
            else:
                self.view()
        elif cmd == 'clean':
            self.clean()
        elif cmd == 'migrate1':
            self.migrate1()
        elif cmd == 'init':
            self.init_db()
        else:
            self.log.error('Command "%s" not recognized' % (cmd,))

    def init_db(self):
        utils.init_db()

    def update(self):
        if len(self.args) > 1:
            ids = self.args[1:]
        utils.update(ids, self.options.queue)

    def sniff(self):
        if len(self.args) < 2:
            print('Not enough arguments', self.args)
            sys.exit(1)
        utils.sniff(self.args[1:])

    def view(self, package_ref=None):
        utils.view(package_ref)

    def clean(self):
        utils.clean()

    def migrate1(self):
        utils.migrate1()
