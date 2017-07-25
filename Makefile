all: install

PROJECT_NAME=access_monitor
PROJECT_HOME=/data/services/$(PROJECT_NAME)
VENV_HOME=$(PROJECT_HOME)/virtualenv

install:
	@mkdir -p $(PROJECT_HOME)/var/etc; \
	mkdir -p $(PROJECT_HOME)/var/run; \
	mkdir -p $(PROJECT_HOME)/var/log; \
	if [ ! -d $(VENV_HOME) ]; \
    then \
        virtualenv $(VENV_HOME); \
        $(VENV_HOME)/bin/pip install -U distribute; \
    fi; \
    $(VENV_HOME)/bin/python setup.py install;\
	cp monit.py $(PROJECT_HOME)
clean:
	@rm -rf access_monitor.egg-info build dist
