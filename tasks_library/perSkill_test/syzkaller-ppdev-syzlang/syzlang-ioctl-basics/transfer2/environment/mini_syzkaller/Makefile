.PHONY: descriptions all

descriptions:
	python3 /opt/syzkaller/tools/validate_task.py

all: descriptions
	python3 -c "from pathlib import Path; Path('/opt/syzkaller/build.ok').write_text('ok\\n', encoding='utf-8')"
