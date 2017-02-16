#!/bin/sh

VERSION_FILE="src/leap/mx/_version.py"
[ -f ${VERSION_FILE} ] && rm ${VERSION_FILE}
echo 'y' | python setup.py freeze_debianver
sed -i 's/-dirty//g' ${VERSION_FILE}
git add ${VERSION_FILE}
git commit -m "[pkg] freeze debian version"
