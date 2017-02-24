#!/bin/sh

VERSION_FILE="src/leap/mx/_version.py"
rm ${VERSION_FILE}
echo y | python setup.py freeze_debianver

# Add the number of commits after last tag to the version string
add_commits=$(git describe | cut -d'-' -f2)
rev=$(git describe | cut -d'-' -f3)
sed -i "/ \"version/s/\"$/.${add_commits}+${rev}\"/" ${VERSION_FILE}

# Remove the -dirty tag
sed -i 's/-dirty//g' ${VERSION_FILE}

git commit -m "[pkg] freeze debian version" ${VERSION_FILE}

python setup.py version
