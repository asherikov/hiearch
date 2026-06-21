PROJECT_NAME=hiearch_dinit

APT_INSTALL=sudo apt install -y --no-install-recommends
# DEB_PYTHON_INSTALL_LAYOUT fixes UNKNOWN -> https://github.com/pypa/setuptools/issues/3269
export DEB_PYTHON_INSTALL_LAYOUT=deb_system
export PYTHONDONTWRITEBYTECODE=1

CURRENT_DIR=$(shell pwd)
BUILD_DIR?=${CURRENT_DIR}/build
TEST_DIR?=${CURRENT_DIR}/test

.DEFAULT:
	@echo "Testing $@..."
	@mkdir -p ${BUILD_DIR}/$@
	${MAKE} test_$@ NAME=$@
	if [ -d "${BUILD_DIR}/$@/services" ]; then \
		# Compare the generated graph with expected output \
		if [ -f "${TEST_DIR}/$@/output/graph.yaml" ]; then \
			echo "Comparing graph output for $@..."; \
			if ! diff -q ${TEST_DIR}/$@/output/graph.yaml ${BUILD_DIR}/$@/graph.yaml >/dev/null 2>&1; then \
				echo "Graph output differs from expected for $@, showing diff:"; \
				diff -u ${TEST_DIR}/$@/output/graph.yaml ${BUILD_DIR}/$@/graph.yaml; \
				exit 1; \
			fi; \
		fi; \
	fi
	if [ -f "${BUILD_DIR}/$@/output/style.yaml" ]; then \
		# Compare the generated style with expected output \
		if [ -f "${TEST_DIR}/$@/output/style.yaml" ]; then \
			echo "Comparing style output for $@..."; \
			if ! diff -q ${TEST_DIR}/$@/output/style.yaml ${BUILD_DIR}/$@/style.yaml >/dev/null 2>&1; then \
				echo "Style output differs from expected for $@, showing diff:"; \
				diff -u ${TEST_DIR}/$@/output/style.yaml ${BUILD_DIR}/$@/style.yaml; \
				exit 1; \
			fi; \
		fi; \
	fi
	@echo "Test $@ passed!"

test_01_basic:
	hiearch_dinit -d ${TEST_DIR}/${NAME}/services > ${BUILD_DIR}/${NAME}/graph.yaml

test_02_complex_deps:
	hiearch_dinit -d ${TEST_DIR}/${NAME}/services -o ${BUILD_DIR}/${NAME}/graph.yaml

test_03_parametrized:
	hiearch_dinit -S ${BUILD_DIR}/${NAME}/style.yaml -d ${TEST_DIR}/${NAME}/services -o ${BUILD_DIR}/${NAME}/graph.yaml

test_04_style_gen:
	hiearch_dinit -S ${BUILD_DIR}/${NAME}/style.yaml

test_05_chain_to:
	hiearch_dinit -d ${TEST_DIR}/${NAME}/services -o ${BUILD_DIR}/${NAME}/graph.yaml

test_06_common_suffix:
	hiearch_dinit -d ${TEST_DIR}/${NAME}/dir1_common ${TEST_DIR}/${NAME}/dir2_common -o ${BUILD_DIR}/${NAME}/graph.yaml

venv: builddir
	python3 -m venv ${BUILD_DIR}/venv

venv_test: clean
	${MAKE} venv
	/bin/sh -c ". ${BUILD_DIR}/venv/bin/activate && pip install . && ${MAKE} test"

test:
	@${MAKE} 01_basic 02_complex_deps 03_parametrized 04_style_gen 05_chain_to 06_common_suffix
	@echo "All CLI tests passed!"

clean:
	rm -Rf .pytest_cache
	rm -Rf ${BUILD_DIR}
	rm -Rf dist
	find ./ -name "__pycache__" | xargs rm -Rf

builddir:
	mkdir -p ${BUILD_DIR}

install:
	pipx install ./
	#${MAKE} clean

install_edit:
	pipx install --editable ./
	${MAKE} clean

# https://packaging.python.org/en/latest/tutorials/packaging-projects/
install_release_deps:
	sudo apt install pipx python3-build python3-packaging
	# apt twine does not work https://github.com/pypi/warehouse/issues/15611
	pipx install twine

upload_testpypi:
	rm -Rf dist
	python3 -m build
	twine upload --verbose --repository testpypi dist/*

upload_pypi:
	rm -Rf dist
	python3 -m build
	twine upload --verbose dist/*

uninstall: clean
	pipx uninstall ${PROJECT_NAME}

reinstall:
	${MAKE}	uninstall
	${MAKE} install

install_deps_apt:
	${APT_INSTALL} python3-yaml pipx

.PHONY: test
