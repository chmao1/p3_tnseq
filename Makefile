TOP_DIR = ../..
include $(TOP_DIR)/tools/Makefile.common

THIS_APP = $(shell basename $(shell pwd))

TRANSIT_SRC = https://github.com/chmao1/transit
TRANSIT_DEPS = pip3 install pytest 'numpy~=1.16' 'scipy==1.11.4' 'matplotlib~=3.0' 'pillow~=6.0' 'statsmodels~=0.9' 'rpy2==3.5.12'
BUILD_VENV = $(shell pwd)/venv
TARGET_VENV = $(TARGET)/venv/$(THIS_APP)

APP_SERVICE = app_service

TARGET ?= /kb/deployment
DEPLOY_RUNTIME ?= /kb/runtime

SRC_SERVICE_PERL = $(wildcard service-scripts/*.pl)
BIN_SERVICE_PERL = $(addprefix $(BIN_DIR)/,$(basename $(notdir $(SRC_SERVICE_PERL))))
DEPLOY_SERVICE_PERL = $(addprefix $(SERVICE_DIR)/bin/,$(basename $(notdir $(SRC_SERVICE_PERL))))

SRC_SERVICE_PYTHON = $(wildcard service-scripts/*.py)
BIN_SERVICE_PYTHON = $(addprefix $(BIN_DIR)/,$(basename $(notdir $(SRC_SERVICE_PYTHON))))
DEPLOY_SERVICE_PYTHON = $(addprefix $(SERVICE_DIR)/bin/,$(basename $(notdir $(SRC_SERVICE_PYTHON))))

all: bin 

bin: $(BIN_PYTHON) $(BIN_SERVICE_PERL) $(BIN_SERVICE_PYTHON)

.PHONY: venv
venv: venv/bin/transit

venv/bin/transit:
	rm -rf transit venv
	git clone $(TRANSIT_SRC) transit
	python3 -m venv $(BUILD_VENV)
	. $(BUILD_VENV)/bin/activate; $(TRANSIT_DEPS)
	cd transit; . $(BUILD_VENV)/bin/activate; python3 setup.py install
	mkdir $(BUILD_VENV)/app-bin
	ln -s ../bin/tpp ../bin/transit $(BUILD_VENV)/app-bin

deploy: deploy-client deploy-service
deploy-all: deploy-client deploy-service
deploy-client: deploy-scripts 

deploy-service: deploy-libs deploy-scripts deploy-service-scripts deploy-specs deploy-venv

deploy-venv:
	rm -rf transit-deploy $(TARGET_VENV)
	git clone $(TRANSIT_SRC) transit-deploy
	$(DEPLOY_RUNTIME)/bin/python3 -m venv $(TARGET_VENV)
	. $(TARGET_VENV)/bin/activate; $(TRANSIT_DEPS)
	cd transit-deploy; . $(TARGET_VENV)/bin/activate; python3 setup.py install
	mkdir $(TARGET_VENV)/app-bin
	ln -s ../bin/tpp ../bin/transit $(TARGET_VENV)/app-bin

$(BIN_DIR)/%: service-scripts/%.pl $(TOP_DIR)/user-env.sh
	export PATH_ADDITIONS=$(BUILD_VENV)/app-bin; \
	$(WRAP_PERL_SCRIPT) '$$KB_TOP/modules/$(CURRENT_DIR)/$<' $@

$(BIN_DIR)/%: service-scripts/%.sh $(TOP_DIR)/user-env.sh
	export PATH_ADDITIONS=$(BUILD_VENV)/app-bin; \
	$(WRAP_SH_SCRIPT) '$$KB_TOP/modules/$(CURRENT_DIR)/$<' $@

$(BIN_DIR)/%: service-scripts/%.py $(TOP_DIR)/user-env.sh
	export PATH_ADDITIONS=$(BUILD_VENV)/app-bin; \
	$(WRAP_PYTHON3_SCRIPT) '$$KB_TOP/modules/$(CURRENT_DIR)/$<' $@

include $(TOP_DIR)/tools/Makefile.common.rules
