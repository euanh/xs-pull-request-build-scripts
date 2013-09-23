# xs-pull-request-build-scripts
Scripts used by the Jenkins Github Pull Request Builder jobs

## Installation
It's importatnt that these scripts are installed in Jenkins' home directory.
This is usually `/var/lib/jenkins/` but it may have been configured differently
at Jenkins installation. SSH into your Jenkins CI server and execute the
following:

```bash
$ cd <JENKINS_HOME>
$ git clone git://github.com/simonjbeaumont/xs-pull-request-build-scripts.git
```

## build-pull-request.sh
This script is used by the Jenkins job and needs to be present in the directory
specified by the install instructions.

Based on the arguments passed to `new-jenkins-job.py`, it will clone the
correct build-system product branch. It will then clone the pull request in
question into `myrepos` and build. The output of the build for each of the
product branches will be collected by Jenkins and archived.

## new-jenkins-job.py
This python script will create a new Github Pull Request Builder related job
for the specified repo. It's usage is as follows:

```bash
$ cd <JENKINS_HOME>/xs-pull-request-build-scripts
$ ./new-jenkins-job.py --help
Usage: new-jenkins-job.py
           [-h|--help]
           [-n|--name] <Repository name>
           [-p|--project-url] <Github project URL>
           [-g|--git-url] <Git URL>
           [-c | --component] <Build system component>
```
