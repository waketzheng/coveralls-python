"""
Publish coverage results online via coveralls.io.

Puts your coverage results on coveralls.io for everyone to see.

This tool makes custom reports for data generated by coverage.py package and
sends it to the coveralls.io service API.

All Python files in your coverage analysis are posted to this service along
with coverage stats, so please make sure you're not ruining your own security!

Usage:
    coveralls [options]
    coveralls debug [options]

    Debug mode doesn't send anything, just outputs json to stdout. It also
    forces verbose output. Please use debug mode when submitting bug reports.

Global options:
    --service=<name>  Provide an alternative service name to submit.
    --rcfile=<file>   Specify configuration file. [default: .coveragerc]
    --basedir=<dir>   Base directory that is removed from reported paths.
    --output=<file>   Write report to file. Doesn't send anything.
    --srcdir=<dir>    Source directory added to reported paths.
    --submit=<file>   Upload a previously generated file.
    --merge=<file>    Merge report from file when submitting.
    --finish          Finish parallel jobs.
    -h --help         Display this help.
    -v --verbose      Print extra info, always enabled when debugging.

Example:
-------
    $ coveralls
    Submitting coverage to coveralls.io...
    Coverage submitted!
    Job #38.1
    https://coveralls.io/jobs/92059
"""
import importlib.metadata
import logging
import sys

import docopt

from .api import Coveralls

log = logging.getLogger('coveralls')


def main(argv=None):
    # pylint: disable=too-complex
    version = importlib.metadata.version('coveralls')
    options = docopt.docopt(__doc__, argv=argv, version=version)
    if options['debug']:
        options['--verbose'] = True

    level = logging.DEBUG if options['--verbose'] else logging.INFO
    log.addHandler(logging.StreamHandler())
    log.setLevel(level)

    token_required = not options['debug'] and not options['--output']

    try:
        coverallz = Coveralls(
            token_required,
            config_file=options['--rcfile'],
            service_name=options['--service'],
            base_dir=options.get('--basedir') or '',
            src_dir=options.get('--srcdir') or '',
        )

        if options['--merge']:
            coverallz.merge(options['--merge'])

        if options['debug']:
            log.info('Testing coveralls-python...')
            coverallz.wear(dry_run=True)
            return

        if options['--output']:
            log.info('Write coverage report to file...')
            coverallz.save_report(options['--output'])
            return

        if options['--submit']:
            with open(options['--submit']) as report_file:
                coverallz.submit_report(report_file.read())
            return

        if options['--finish']:
            log.info('Finishing parallel jobs...')
            coverallz.parallel_finish()
            log.info('Done')
            return

        log.info('Submitting coverage to coveralls.io...')
        result = coverallz.wear()

        log.info('Coverage submitted!')
        log.debug(result)
        if result:
            log.info(result.get('message'))
            log.info(result.get('url'))
    except KeyboardInterrupt:  # pragma: no cover
        log.info('Aborted')
    except Exception as e:
        log.exception('Error running coveralls: %s', e)
        sys.exit(1)
