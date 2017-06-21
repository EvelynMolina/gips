import logging, os, shutil, re
import importlib
from pprint import pformat

import pytest
from scripttest import TestFileEnvironment, ProcResult, FoundFile, FoundDir
import envoy

from gips.inventory import orm # believed to be safe even though it's the code under test

_log = logging.getLogger(__name__)


def set_constants(config):
    """Use pytest config API to set globals pointing at needed file paths."""
    global TEST_DATA_DIR, DATA_REPO_ROOT, OUTPUT_DIR, NH_SHP_PATH, DURHAM_SHP_PATH, NE_SHP_PATH
    TEST_DATA_DIR  = str(config.rootdir.join('gips/test'))
    DATA_REPO_ROOT = config.getini('data-repo')
    OUTPUT_DIR     = config.getini('output-dir')
    NH_SHP_PATH    = os.path.join(TEST_DATA_DIR, 'NHseacoast.shp')
    NE_SHP_PATH    = os.path.join(TEST_DATA_DIR, 'NE.shp')
    DURHAM_SHP_PATH = os.path.join(TEST_DATA_DIR, 'durham.shp')

slow = pytest.mark.skipif('not config.getoption("slow")',
                          reason="--slow is required for this test")
acolite = pytest.mark.skipif('not config.getoption("acolite")',
                          reason="--acolite is required for this test")
sys = pytest.mark.skipif('not config.getoption("sys")', reason="--sys is required for this test")


def extract_hashes(files):
    """Return a dict of file names and unique hashes of their content.

    `files` should be a dict in a result object from TestFileEnvironment.run().
    Directories' don't have hashes so use None instead."""
    return {k: getattr(v, 'hash', None) for k, v in files.items()}


def extract_timestamps(files):
    """Return a dict of file names and unique hashes of their content.

    `files` should be a dict in a result object from TestFileEnvironment.run().
    Directories' don't have hashes so use None instead."""
    return {k: getattr(v, 'hash', None) for k, v in files.items()}


class GipsTestFileEnv(TestFileEnvironment):
    """As superclass but customized for GIPS use case.

    Saves ProcResult objects in self.proc_result."""
    proc_result = None

    @staticmethod
    def log_findings(description, files):
        """If user asks for debug output, log post-run file findings.

        Logs in a format suitable for updating known good values when tests
        need to be updated to match code changes."""
        _log.debug("{}: {}".format(description, pformat(files)))

    def run(self, *args, **kwargs):
        """As super().run but store result & prevent premature exits."""
        logging.debug("command line: `{}`".format(' '.join(args)))
        self.proc_result = super(GipsTestFileEnv, self).run(
            *args, expect_error=True, expect_stderr=True, **kwargs)
        self.gips_proc_result = gpr = GipsProcResult(self.proc_result)
        logging.debug("standard output: {}".format(
            gpr.stdout if gpr.stdout != '' else '(None)'))
        logging.debug("standard error: {}".format(
            gpr.stderr if gpr.stderr != '' else '(None)'))
        if pytest.config.getoption("--expectation-format"):
            print ('standard output (expectation format): """' +
                   re.sub('\\\\n', '\n', repr(gpr.stdout))[2:-1] + '"""')
            print ('standard error (expectation format):  """' +
                   re.sub('\\\\n', '\n', repr(gpr.stderr))[2:-1] + '"""')
        self.log_findings("Created files", gpr.created)
        self.log_findings("Updated files", gpr.updated)
        self.log_findings("Deleted files", gpr.deleted)
        return gpr

    def remove_created(self, strict=False):
        """Remove files & directories created by test run."""
        if self.proc_result is None:
            msg = "No previous run to clean up from."
            if strict:
                raise RuntimeError(msg)
            else:
                _log.warning("Can't remove_created: " + msg)
                return

        created = self.proc_result.files_created
        # first remove all the files
        fn = [n for (n, t) in created.items() if isinstance(t, FoundFile)]
        [os.remove(os.path.join(DATA_REPO_ROOT, n)) for n in fn]
        # then remove all the directories (which should now be empty)
        dn = [n for (n, t) in created.items() if isinstance(t, FoundDir)]
        for n in dn:
            # dirs are complex because they can exist inside eachother
            full_n = os.path.join(DATA_REPO_ROOT, n)
            if os.path.lexists(full_n):
                shutil.rmtree(full_n)

    def _find_files(self, *args, **kwargs):
        """As super, but log that the checksums are being computed.

        Logs are needed because the process takes time for large assets."""
        _log.debug("Starting file detection & checksumming")
        rv = super(GipsTestFileEnv, self)._find_files(*args, **kwargs)
        _log.debug("Completed file detection & checksumming")
        return rv


class GipsProcResult(object):
    """Storage & equality comparison for a process's various outcomes.

    Standard output is handled specially for equality comparison; see __eq__.
    Can accept scripttest.ProcResult objects at initialization; see __init__.
    """
    attribs = ('exit_status', 'stdout', 'stderr', 'updated', 'deleted',
               'created', 'ignored',)  # 'timestamps')

    def __init__(self, proc_result=None, compare_stdout=None, compare_stderr=True, **kwargs):
        """Initialize the object using a ProcResult, explicit kwargs, or both.

        ProcResults' reports on files (created, deleted, updated) are saved as
        their names and hashes.  compare_stdout is an explicit way to request
        stdout be considered in __eq__; see below.  If it is not set, then
        self.stdout is examined.  If set by the user, it is assumed stdout
        comparison is desired.  compare_stderr is less magical:  Do the
        comparison unless the user specifies otherwise.
        """
        if proc_result is None:
            self.exit_status = 0
            self.stdout = None
            self.stderr = u''
            self.updated = {}
            self.deleted = {}
            self.created = {}
            # self.timestamps = {}
        else:
            # self.proc_result = proc_result # not sure if this is needed
            self.exit_status = proc_result.returncode
            self.stdout = proc_result.stdout
            self.stderr = proc_result.stderr
            self.updated = extract_hashes(proc_result.files_updated)
            self.deleted = extract_hashes(proc_result.files_deleted)
            self.created = extract_hashes(proc_result.files_created)
            # self.timestamps = dict()
            # for files in [proc_result.files_updated, proc_result.files_created]:
            #     self.timestamps.update(extract_timestamps(files))

        self.ignored = []  # list of filenames to ignore for comparison purposes

        # special keys are permitted if they begin with an underscore
        input_fields = set(k for k in kwargs.keys() if k[0] != '_')
        if not input_fields.issubset(set(self.attribs)):
            raise ValueError('Unknown attributes for GipsProcResult',
                             list(input_fields - set(self.attribs)))

        self.__dict__.update(kwargs)  # set user's desired values

        # guess the user's wishes regarding stdout comparison;
        # explicit request should override guesswork
        if compare_stdout is not None:
            self.compare_stdout = compare_stdout
        else:
            self.compare_stdout = self.stdout is not None
        # need a valid value to compare against either way
        # self.stdout = self.stdout or u''
        self.compare_stderr = compare_stderr

    def strip_ignored(self, d):
        """Return a copy of dict d but strip out items in self.ignored.

        If self.ignored = ['a', 'b'] then
        strip_ignored({'a': 1, 'b': 2, 'c': 2}) returns {'c': 2}.
        """
        return {k: v for k, v in d.items() if k not in self.ignored}

    def __eq__(self, other):
        """Equality means all attributes must match, except possibly stdout & stderr.

        Note that the type of other is not considered.
        """
        # only compare standard streams if both parties agree
        compare_stdout = self.compare_stdout and other.compare_stdout
        compare_stderr = self.compare_stderr and other.compare_stderr
        matches = (
            self.exit_status == other.exit_status,
            not compare_stdout or self.stdout == other.stdout,
            not compare_stderr or self.stderr == other.stderr,
            self.strip_ignored(self.updated) == self.strip_ignored(other.updated),
            self.strip_ignored(self.deleted) == self.strip_ignored(other.deleted),
            self.strip_ignored(self.created) == self.strip_ignored(other.created),
        )
        return all(matches)


def rectify(driver):
    """Ensure inv DB matches files on disk."""
    if not orm.use_orm():
        return
    rectify_cmd = 'gips_inventory {} --rectify'.format(driver)
    outcome = envoy.run(rectify_cmd)
    if outcome.status_code != 0:
        raise RuntimeError("failed: " + rectify_cmd,
                           outcome.std_out, outcome.std_err, outcome)


@pytest.yield_fixture
def repo_env(request):
    """Provide means to test files created by run & clean them up after."""
    if not orm.use_orm():
        _log.warning("ORM is deactivated; check GIPS_ORM.")
    gtfe = GipsTestFileEnv(DATA_REPO_ROOT, start_clear=False)
    yield gtfe
    # This step isn't effective if DATA_REPO_ROOT isn't right; in that case it
    # ruins further test runs because files already exist when the test starts.
    # Maybe add self-healing by having setup_modis_data run in a TFE and
    # detecting which files are present when it starts.
    gtfe.remove_created()
    rectify(request.module.driver)


@pytest.yield_fixture(scope='module')
def clean_repo_env(request):
    """Keep data repo clean without having to run anything in it.

    This emulates tfe.run()'s checking the directory before and after a run,
    then working out how the directory has changed.  Unfortunately half the
    work is done in tfe, the other half in ProcResult."""
    if not orm.use_orm():
        _log.warning("ORM is deactivated; check GIPS_ORM.")
    file_env = GipsTestFileEnv(DATA_REPO_ROOT, start_clear=False)
    before = file_env._find_files()
    _log.debug("Generating file env: {}".format(file_env))
    yield file_env
    after = file_env._find_files()
    file_env.proc_result = ProcResult(file_env, ['N/A'], '', '', '', 0, before, after)
    file_env.remove_created()
    rectify(request.module.driver)
    _log.debug("Finalized file env: {}".format(file_env))


@pytest.fixture
def output_tfe():
    """Provide means to test files created by run & clean them up after."""
    gtfe = GipsTestFileEnv(OUTPUT_DIR)
    return gtfe


@pytest.fixture
def expected(request):
    """Use introspection to find known-good values for test assertions.

    For example, assume this test is in t_modis.py:

        def t_process(setup_modis_data, repo_env, expected):
            '''Test gips_process on modis data.'''
            actual = repo_env.run('gips_process', *STD_ARGS)
            assert expected == actual

    Then expected() will end up looking in expected/modis.py for `t_process`:

            t_process = {
                'updated': {...},
                'created': {...},
            }
    """
    # construct expectation module name from test module name:
    # e.g.:  'foo.bar.t_baz_qux' -> 'baz_qux'
    mod_name = request.module.__name__.split('.')[-1].split('_', 1)[1]
    relative_mod_name = '..expected.' + mod_name
    try:
        module = importlib.import_module(relative_mod_name, __name__)
    except ImportError as ie:
        msg = "Eror importing expectations from {}.".format(relative_mod_name)
        raise ImportError(msg, ie.args)
    return GipsProcResult(**getattr(module, request.function.func_name))
