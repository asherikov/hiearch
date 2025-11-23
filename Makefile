PROJECT_NAME=hiearch

APT_INSTALL=sudo apt install -y --no-install-recommends
# DEB_PYTHON_INSTALL_LAYOUT fixes UNKNOWN -> https://github.com/pypa/setuptools/issues/3269
export DEB_PYTHON_INSTALL_LAYOUT=deb_system
export PYTHONDONTWRITEBYTECODE=1

CURRENT_DIR=$(shell pwd)
BUILD_DIR?=${CURRENT_DIR}/build
TEST_DIR?=${CURRENT_DIR}/test
TEST_NOT=
FORMAT=svg

.DEFAULT:
	@echo "Testing $@..."
	mkdir -p ${BUILD_DIR}/$@
	cp ${TEST_DIR}/$@/icon*.svg ${BUILD_DIR}/$@/ || true
	cd ${TEST_DIR}/$@/; ${TEST_NOT} hiearch -f ${FORMAT} -o ${BUILD_DIR}/$@ *.yaml
	# TODO awkward and fragile
	find ${BUILD_DIR}/$@/ -iname '*.gv' | sort | xargs --no-run-if-empty -I {} sh -c "sort {} | md5sum > ${BUILD_DIR}/$@/checksum.build && basename '{}' >> ${BUILD_DIR}/$@/checksum.build"
	find ${TEST_DIR}/$@/ -iname '*.gv' | sort | xargs --no-run-if-empty -I {} sh -c "sort {} | md5sum > ${BUILD_DIR}/$@/checksum.test && basename '{}' >> ${BUILD_DIR}/$@/checksum.test"
	${TEST_NOT} cmp ${BUILD_DIR}/$@/checksum.build ${BUILD_DIR}/$@/checksum.test

venv: builddir
	python3 -m venv ${BUILD_DIR}/venv

venv_test: clean
	${MAKE} venv
	/bin/sh -c ". ${BUILD_DIR}/venv/bin/activate && ${MAKE} install && ${MAKE} test"

venv_install: venv
	/bin/sh -c ". ${BUILD_DIR}/venv/bin/activate && ${MAKE} install"

test:
	@${MAKE} \
		01_basic 02_default_view 03_default_view_split 06_multiscope \
		07_trivial 08_node_realations 09_tags 10_minimal \
		11_neighbors 12_view_style 13_edge_labels 14_edge_style \
		15_formatted_labels 16_state_machine 17_use_case 18_style_notag \
		21_dinit_service_style 22_style_notag_tag_inheritance || (echo "Failure!" && false)
	@${MAKE} TEST_NOT=! 04_node_cycle 05_style_cycle 19_style_notag_cycle \
		20_mixed_style_cycle || (echo "Failure!" && false)
	@echo "Success!"

clean:
	rm -Rf .pytest_cache
	rm -Rf ${BUILD_DIR}
	rm -Rf dist
	find ./ -name "__pycache__" | xargs rm -Rf

builddir:
	mkdir -p ${BUILD_DIR}

install:
	pip install --no-cache-dir ./
	#${MAKE} clean

install_edit:
	pip install --editable ./
	${MAKE} clean

install_deps: builddir
	pip-compile --verbose --output-file ./${BUILD_DIR}/requirements.txt pyproject.toml
	pip install -r ./${BUILD_DIR}/requirements.txt

# https://packaging.python.org/en/latest/tutorials/packaging-projects/
install_release_deps:
	#pip install --upgrade build
	#pip install --upgrade twine
	#pip install --upgrade packaging
	pipx install twine
	# apt twine does not work https://github.com/pypi/warehouse/issues/15611
	sudo apt install python3-build python3-packaging

upload_testpypi:
	rm -Rf dist
	python3 -m build
	twine upload --verbose --repository testpypi dist/*

upload_pypi:
	rm -Rf dist
	python3 -m build
	twine upload --verbose dist/*

uninstall: clean
	pip uninstall -y ${PROJECT_NAME}

reinstall:
	${MAKE}	uninstall
	${MAKE} install

spell:
	hunspell README.md

install_deps_apt:
	${APT_INSTALL} graphviz

svg2png:
	find ${DIR} -iname "*.svg" | sed -e "s/\.svg$$//" | xargs -I {} sh -c "rsvg-convert {}.svg --format=png --output={}.png"

fmt:
	cp README.md README.md.back
	sed '/^Introduction$$/,$$!d' README.md.back > README.md
	pandoc --standalone --columns=80 --markdown-headings=setext --tab-stop=2 --to=gfm --toc --toc-depth=2 README.md -o README.fmt.md
	mv README.fmt.md README.md


.PHONY: test

# https://packaging.python.org/en/latest/tutorials/packaging-projects/
