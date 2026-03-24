#!/bin/bash
set -e

cat > /opt/syzkaller/sys/linux/dev_uinput.txt.const <<'EOF'
# Constants for the uinput scaffold.
arches = amd64, 386

UI_DEV_CREATE = 21761
UI_DEV_DESTROY = 21762
UI_DEV_SETUP = 1079792899
UI_ABS_SETUP = 1075598596
UI_GET_VERSION = 2147767597
UI_SET_EVBIT = 1074025828
UI_SET_KEYBIT = 1074025829
UI_SET_RELBIT = 1074025830
UI_SET_PROPBIT = 1074025838

EV_KEY = 1
EV_REL = 2
KEY_SPACE = 57
BTN_LEFT = 272
REL_X = 0
REL_Y = 1
INPUT_PROP_POINTER = 0
EOF

cd /opt/syzkaller
make descriptions
