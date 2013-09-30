#!/usr/bin/python

import os
import sys
import re
import subprocess
import shutil
import time
import glob

LOCAL_BUILD_SPACE = "/usr/local/builds/jenkins"
REQUIRED_ENV_VARS = ['ghprbTargetBranch', 'ghprbPullId', 'ghprbActualCommit',
                     'WORKSPACE', 'BUILD_TAG', 'GIT_URL', 'sha1',
                     'build_system_component']


def execute(command):
    rc = subprocess.call(command.split())
    if rc != 0:
        raise Exception("Error executing command %s: Return code = %s" %
                        (command, rc))


def print_heading(msg):
    print "-" * 80
    print msg


def assert_environment_contains_vars(var_names):
    for var in var_names:
        print "Checking environment variable '%s' exists..." % var,
        try:
            assert var in os.environ
            print "OK"
        except AssertionError:
            print "Fail"
            sys.exit(1)


def repo_name_of_git_url(git_url):
    return git_url.split('/')[-1].split('.')[0]


def get_local_branches_for_repo(repo, github_branch):
    with open("/home/xenhg/git-subscriptions") as f:
        p = re.compile("\s%s\srefs/heads/%s\s" % (repo, github_branch))
        branches = []
        for line in [l for l in f.readlines() if p.search(l)]:
            print "Found relevant line in git subscriptions:"
            print "\t%s" % line
            branches.append(line.split()[4].split('/')[1])
    return branches


def cleanup_job():
    print_heading("Deleting temporary build root...")
    execute("sudo rm -rf /usr/local/builds/jenkins/%s" %
            os.environ['BUILD_TAG'])


def main():
    print_heading("Pull request detected!")
    print_heading("Checking Jenkins job properly configured...")
    assert_environment_contains_vars(REQUIRED_ENV_VARS)
    repo_name = repo_name_of_git_url(os.environ['GIT_URL'])
    print "Repo: %s" % repo_name
    print "Github target branch: %s" % os.environ['ghprbTargetBranch']
    print "Pull request #: %s" % os.environ['ghprbPullId']
    print "Ref: %s" % os.environ['sha1']
    print "Commit: %s" % os.environ['ghprbActualCommit']

    print_heading("Removing artifacts from previous job...")
    for rpm_dir in glob.glob(os.path.join(os.environ['WORKSPACE'], 'rpms-*')):
        shutil.rmtree(rpm_dir, True)

    print_heading("Finding local branches for Github branch '%s' of '%s'..." %
                  (os.environ['ghprbTargetBranch'], os.environ['GIT_URL']))
    local_branches = get_local_branches_for_repo(
        repo_name, os.environ['ghprbTargetBranch'])
    if len(local_branches) == 0:
        print "Error: Local build branch not found in git-subscriptions."
        sys.exit(2)
    else:
        print ("Github branch '%s' -> local branches '%s'" %
               (os.environ['ghprbTargetBranch'], local_branches))
        if len(local_branches) > 1:
            print "All local branches will be built..."

    for local_branch in local_branches:
        print_heading("Starting build for local branch '%s'" % local_branch)
        print "Fetching local branch '%s' from build system..." % local_branch
        build_hg_path = os.path.join(LOCAL_BUILD_SPACE,
                                     os.environ['BUILD_TAG'], local_branch)
        os.makedirs(build_hg_path)
        execute("hg clone http://hg/carbon/%s/build.hg %s" %
                (local_branch, build_hg_path))

        print_heading("Injecting repo into build.hg/myrepos...")
        local_repo = os.path.join(build_hg_path, "myrepos", repo_name)
        execute("git clone file://%s %s" %
                (os.environ['WORKSPACE'], local_repo))
        git_exe = "git --git-dir=%s/.git" % local_repo
        execute("%s remote set-url origin %s" %
                (git_exe, os.environ['GIT_URL']))
        execute("%s status" % git_exe)

        print_heading("Start the build...")

        execute("make --directory=%s manifest-latest" % build_hg_path)
        execute("make --directory=%s %s-build" %
                (build_hg_path, os.environ['build_system_component']))

        print_heading("Extracting RPMs from '%s' build.hg for archive..." %
                      local_branch)
        rpms_dir = os.path.join(os.environ['WORKSPACE'],
                                "rpms-%s" % local_branch)

        os.mkdir(rpms_dir)
        for rpm in glob.glob(os.path.join(build_hg_path, "output",
                                          os.environ['build_system_component'],
                                          "RPMS/i686/*")):
            print "Copying RPM: %s -> %s..." % (rpm, rpms_dir),
            shutil.copy(rpm, rpms_dir)
            print "OK"

        print_heading("Deleting build.hg for local branch '%s'" % local_branch)
        # Retry in case bind mounts haven't released
        for _ in range(1, 5):
            try:
                time.sleep(3)
                execute("sudo rm -rf %s" % build_hg_path)
            except:
                print "Deletion failed, sleeping for 3 seconds and retrying..."
        if os.path.exists(build_hg_path):
            raise Exception("Cannot delete build.hg after build!")

    cleanup_job()

    print_heading("End of build script")
    print_heading("")

if __name__ == "__main__":
    try:
        main()
    except Exception, e:
        print_heading("Job failed, attempting cleanup...")
        try:
            cleanup_job
        except:
            print_heading("Warning: Cleanup failed!")