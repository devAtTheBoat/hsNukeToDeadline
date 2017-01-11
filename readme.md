# How to connect to this repository


## Ask Kim for HELP!


### Choose an Installation Method

There are a number of different ways to install the AWS CLI on your machine, depending on what operating system and environment you are using:

On Microsoft Windows – use the MSI installer. 
http://docs.aws.amazon.com/cli/latest/userguide/installing.html#install-msi-on-windows

On Linux, OS X, or Unix – use pip (a package manager for Python software) or install manually with the bundled installer.
http://docs.aws.amazon.com/cli/latest/userguide/installing.html#install-bundle-other-os

Note
On OS X, if you see an error regarding the version of six that came with distutils in El Capitan, use the --ignore-installed option:

    $ sudo pip install awscli --ignore-installed six

The awscli package may be available in repositories for other package managers such as APT, yum and Homebrew, but it is not guaranteed to be the latest version. To make sure you have the latest version, use one of the installation methods described here.

### Configure a credential helper for your profile. From the terminal or command prompt, run:
aws configure --profile developer 
to set up a profile to use with AWS CodeCommit. 
Replace the red steps with your own information:

    AWS Access Key ID [None]: Type your AWS access key ID here, and then press Enter
    AWS Secret Access Key [None]: Type your AWS secret access key here, and then press Enter
    Default region name [None]: Type us-east-1 here, and then press Enter
    Default output format [None]: Type json here, and then press Enter
    
### Configure Git to use the AWS CodeCommit credential helper. From the terminal or command prompt, run the following two commands:

    git config --global credential.helper '!aws --profile developer codecommit credential-helper $@' 
    git config --global credential.UseHttpPath true
    
### Switch to a directory of your choice and clone the AWS CodeCommit repository to your local machine by running the following command:

    git clone ssh://APKAI3YP24TE4ROXALBQ@git-codecommit.us-east-1.amazonaws.com/v1/repos/theboatConfigFolder .
    
That's it!