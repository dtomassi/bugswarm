import re

from os.path import isfile

from bugswarm.common import log
from reproducer.utils import Utils


def modify_build_sh(repo: str, build_sh_path: str):
    """
    Travis builds are sometimes not reproducible when run using the build.sh script ("the build script") generated by
    travis-build. Thus, to increase the number of reproducible builds, we modify the build script.

    This function applies the necessary modifications to the build script located at `build_sh_path` and writes the
    modified file to that same location.

    This set of modifications was developed over time as we observed more build reproducibility issues that were likely
    caused by using the build script generated by travis-build.

    There's a file in Google Drive that explains the modifications applied to the build script.

    A previous version of this function included several additional build script modifications that have since been
    removed because travis-build was patched to generate build scripts that need fewer modifications. The BugSwarm
    pipeline utilizes the patched version of travis-build to generate build scripts.

    :param repo: A GitHub repository slug
    :param build_sh_path: The path to the unmodified build script (generated by travis-build).
    """
    if not isinstance(repo, str):
        raise TypeError
    if not repo:
        raise ValueError
    if not isinstance(build_sh_path, str):
        raise TypeError
    if not build_sh_path:
        raise ValueError

    log.debug('Modifying build script at {}.'.format(build_sh_path))

    # Read and modify the original build script.
    lines = []
    with open(build_sh_path) as f:
        skip = False
        for line in f:
            if 'start git.checkout' in line:
                skip = True
            elif 'travis_fold end git.checkout' in line:
                skip = False
                lines.append(r'travis_cmd cd\ ' + repo + ' --assert --echo\n')
            else:
                if not skip:
                    lines.append(line)

    # Overwrite the original build script with the modified build script.
    Utils.remove_file(build_sh_path)
    with open(build_sh_path, 'w') as f2:
        for l in lines:
            f2.write(l)


def patch_build_script(build_sh_path: str):
    """
    Adds flag for Maven to force TLS 1.2 in build scripts for Java jobs using JDK 7.

    :param build_sh_path: The path to a build script.
    """

    if not isinstance(build_sh_path, str):
        raise TypeError
    if not build_sh_path:
        raise ValueError
    if not isfile(build_sh_path):
        msg = '{} is not a file.'.format(build_sh_path)
        log.error(msg)
        raise OSError(msg)

    lines = []
    try:
        with open(build_sh_path) as f:
            for line in f:
                # Matches travis_cmd mvn\ ...
                match_obj = re.search(r'mvn[^w][\\]?', line)
                if not match_obj:
                    lines.append(line)
                    continue

                # Negative look behind. Catches case of no \ before the first -
                # Ex: travis_cmd mvn\ clean\ cobertura:cobertura\ coveralls:report --echo --timing
                match_obj = re.search(r'(?<![^\\]) -', line)
                if match_obj:
                    lines.append(line.replace(' -', r' -Dhttps.protocols=TLSv1.2\ -', 1))
                    continue
                # Negative look behind. Catches case of a \ before the first -
                # Ex: travis_cmd mvn\ clean\ cobertura:cobertura\ coveralls:report\ --echo --timing
                match_obj = re.search(r'((?<![\\]) -)', line)
                if match_obj:
                    lines.append(line.replace(' -', r'\ -Dhttps.protocols=TLSv1.2 -', 1))
                    continue
    except IOError:
        log.error('Error reading {} for patching mvn commands to use TLSv1.2.'.format(build_sh_path))
        raise

    # Overwrite the original build script with the modified build script.
    try:
        with open(build_sh_path, 'w') as f:
            for l in lines:
                f.write(l)
    except IOError:
        log.error('Error writing {} for patching mvn commands to use TLSv1.2.'.format(build_sh_path))
        raise
