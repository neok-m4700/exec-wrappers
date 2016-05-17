import os
import pytest

import stat
import sys

from exec_wrappers import create_wrappers
from exec_wrappers.create_wrappers import list_executable_files, create_conda_wrappers, \
    create_schroot_wrappers, get_templates_dir, get_wrapper_extension


def test_list_executable_files(tmpdir):
    executable_filename = _create_executable_file(tmpdir.join('executable_filename'))

    _create_non_executable_file(tmpdir.join('non_executable'))

    assert list_executable_files(str(tmpdir)) == [str(executable_filename)]


def test_list_executable_files_sorted(tmpdir):
    filename_1 = _create_executable_file(tmpdir.join('1_executable'))
    filename_2 = _create_executable_file(tmpdir.join('j_executable'))
    filename_3 = _create_executable_file(tmpdir.join('z_executable'))

    assert list_executable_files(str(tmpdir)) == [
        str(filename_1),
        str(filename_2),
        str(filename_3)
    ]


def _create_executable_file(filepath):
    if sys.platform == 'win32':
        filepath = filepath.new(ext='bat')

    filepath.write('')
    if sys.platform != 'win32':
        filepath.chmod(filepath.stat().mode | stat.S_IXUSR)

    return filepath


def _create_non_executable_file(filepath):
    filepath.write('')
    return filepath


WRAPPER_CREATOR_AND_ARGS = [
    (create_conda_wrappers, {'conda_env_dir': 'miniconda/envs/test'}),
]
if sys.platform.startswith('linux'):
    WRAPPER_CREATOR_AND_ARGS.extend([
        (create_schroot_wrappers, {'schroot_name': 'ubuntu-14.04'}),
    ])


@pytest.mark.parametrize(('wrapper_creator', 'extra_kwargs'), WRAPPER_CREATOR_AND_ARGS)
def test_create_wrappers(wrapper_creator, extra_kwargs, tmpdir):
    wrappers_dir = tmpdir.join('wrappers')
    bin_dir = tmpdir.join('bin')

    kwargs = {
        'files_to_wrap': [str(bin_dir.join('python')), str(bin_dir.join('gcc'))],
        'destination_dir': str(wrappers_dir),
    }
    kwargs.update(extra_kwargs)
    wrapper_creator(**kwargs)

    _check_wrappers(wrappers_dir, ['run-in', 'python', 'gcc'])


WRAPPER_TYPE_AND_ARGS = [
    ('conda', (['--conda-env-dir', 'miniconda/envs/test'])),
]
if sys.platform.startswith('linux'):
    WRAPPER_TYPE_AND_ARGS.extend([
        ('schroot', (['--schroot-name', 'ubuntu-14.04'])),
    ])


@pytest.mark.parametrize(('wrapper_type', 'extra_args'), WRAPPER_TYPE_AND_ARGS)
def test_create_wrappers_from_main(wrapper_type, extra_args, tmpdir):
    wrappers_dir = tmpdir.join('wrappers')
    bin_dir = tmpdir.join('bin')
    bin_dir.mkdir()
    _create_executable_file(bin_dir.join('python'))
    _create_executable_file(bin_dir.join('gcc'))

    create_wrappers._main([
        '-t', wrapper_type,
        '--bin-dir', str(bin_dir),
        '--dest-dir', str(wrappers_dir),
    ] + extra_args)

    _check_wrappers(wrappers_dir, ['run-in', 'python', 'gcc'])


@pytest.mark.parametrize(('wrapper_type', 'extra_args'), WRAPPER_TYPE_AND_ARGS)
def test_create_only_given_wrappers_from_main(wrapper_type, extra_args, tmpdir):
    wrappers_dir = tmpdir.join('wrappers')

    create_wrappers._main([
        '-t', wrapper_type,
        '--files-to-wrap', 'python:gcc',
        '--dest-dir', str(wrappers_dir),
    ] + extra_args)

    _check_wrappers(wrappers_dir, ['run-in', 'python', 'gcc'])


@pytest.mark.skipif(sys.platform != 'win32', reason='Extension handling only on Windows')
def test_omit_original_extension(tmpdir):
    wrappers_dir = tmpdir.join('wrappers')
    bin_dir = tmpdir.join('bin')
    create_conda_wrappers([str(bin_dir.join('python.exe')), str(bin_dir.join('gcc.bat'))],
                          'miniconda/envs/test',
                          str(wrappers_dir))

    _check_wrappers(wrappers_dir, ['run-in', 'python', 'gcc'])


def test_dont_create_wrapper_when_file_has_same_name(tmpdir):
    wrappers_dir = tmpdir.join('wrappers')
    bin_dir = tmpdir.join('bin')
    os.makedirs(str(bin_dir))
    # It should not create a wrapper for run-in, otherwise it will overwrite
    _create_executable_file(bin_dir.join('run-in'))

    create_conda_wrappers([str(bin_dir.join('python')), str(bin_dir.join('gcc'))],
                          str(wrappers_dir),
                          'miniconda/envs/test')

    with open(os.path.join(get_templates_dir(), 'conda', 'run-in' + get_wrapper_extension())) as f:
        expected_run_in_content = f.read().replace('@CONDA_ENV_DIR@', 'miniconda/envs/test')

    assert wrappers_dir.join('run-in' + get_wrapper_extension()).read() == expected_run_in_content


def _check_wrappers(wrappers_dir, basenames):
    obtained_wrappers = sorted([f.basename for f in wrappers_dir.listdir()])
    expected_wrappers = sorted([f + get_wrapper_extension() for f in basenames])

    assert obtained_wrappers == expected_wrappers

    for f in wrappers_dir.listdir():
        assert os.access(str(f), os.X_OK)
