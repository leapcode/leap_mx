#!/bin/zsh

VERSION_FILE="src/leap/mx/_version.py"
rm ${VERSION_FILE}
python setup.py freeze_debianver
sed -i 's/-dirty//g' ${VERSION_FILE}
git add ${VERSION_FILE}
git commit -m "freeze debian version"
