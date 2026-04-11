PROJECT_NAME=hiearch

APT_INSTALL=sudo apt install -y --no-install-recommends
# DEB_PYTHON_INSTALL_LAYOUT fixes UNKNOWN -> https://github.com/pypa/setuptools/issues/3269
export DEB_PYTHON_INSTALL_LAYOUT=deb_system
export PYTHONDONTWRITEBYTECODE=1

CURRENT_DIR=$(shell pwd)
DIAGRAMS_RESOURCES=$(shell find ${HOME} ${PIPX_HOME} ${PIPX_GLOBAL_HOME} -ipath "*/resources/alibabacloud" | head -1 | xargs -I {} dirname {})
BUILD_DIR?=${CURRENT_DIR}/build
TEST_DIR?=${CURRENT_DIR}/test
TEST_NOT=
FORMAT?=svg

.DEFAULT:
	@echo "Testing $@..."
	mkdir -p ${BUILD_DIR}/$@
	cp ${TEST_DIR}/$@/icon*.svg ${BUILD_DIR}/$@/ || true
	cd ${TEST_DIR}/$@/; ${TEST_NOT} (find ./ -iname "*.yaml" -or -iname "*.dot" | xargs hiearch -f ${FORMAT} -r ${DIAGRAMS_RESOURCES} -o ${BUILD_DIR}/$@)
	# TODO awkward and fragile
	find ${BUILD_DIR}/$@/ -iname '*.gv' | sort | xargs --no-run-if-empty -I {} sh -c "sort {} | md5sum && basename '{}'" >> ${BUILD_DIR}/$@/checksum.build
	find ${TEST_DIR}/$@/ -iname '*.gv' | sort | xargs --no-run-if-empty -I {} sh -c "sort {} | md5sum && basename '{}'" >> ${BUILD_DIR}/$@/checksum.test
	${TEST_NOT} test -s "${BUILD_DIR}/$@/checksum.build" && cmp ${BUILD_DIR}/$@/checksum.build ${BUILD_DIR}/$@/checksum.test
	${TEST_NOT} (cd ${BUILD_DIR}/$@/ && ls *.${FORMAT} && ls *.gv | sed 's/\.gv//' | xargs --no-run-if-empty -I {} test -f {}.${FORMAT})

31_temp_dir:
	mkdir -p ${BUILD_DIR}/$@ ${BUILD_DIR}/$@/temp
	cd ${TEST_DIR}/$@/; hiearch -f ${FORMAT} -o ${BUILD_DIR}/$@ -t ${BUILD_DIR}/$@/temp input.yaml
	test -f "${BUILD_DIR}/$@/simple_view.svg"
	test -f "${BUILD_DIR}/$@/temp/simple_view.gv"
	test ! -f "${BUILD_DIR}/$@/simple_view.gv"

35_skill_install:
	mkdir -p ${BUILD_DIR}/$@
	rm -rf ${BUILD_DIR}/$@/
	hiearch --install-skill ${BUILD_DIR}/$@/
	test -d "${BUILD_DIR}/$@/hiearch"
	test -f "${BUILD_DIR}/$@/hiearch/SKILL.md"

36_list_styles:
	mkdir -p ${BUILD_DIR}/$@
	hiearch --list-styles > ${BUILD_DIR}/$@/output.txt
	test $$(wc -l < ${BUILD_DIR}/$@/output.txt) -ge 20

venv: builddir
	python3 -m venv ${BUILD_DIR}/venv

venv_test: clean
	${MAKE} venv
	/bin/sh -c ". ${BUILD_DIR}/venv/bin/activate && pip install . && ${MAKE} test"

venv_test_quick:
	rm -rf build/${TEST}/*
	/bin/sh -c ". ${BUILD_DIR}/venv/bin/activate && pip install . && ${MAKE} ${TEST}"

test:
	@${MAKE} \
		01_basic 02_default_view 03_default_view_split 06_multiscope \
		07_trivial 08_node_realations 09_tags 10_minimal \
		11_neighbors 12_view_style 13_edge_labels 14_edge_style \
		15_formatted_labels 16_state_machine 17_use_case 18_style_notag \
		22_style_notag_tag_inheritance 23_expand \
		25_dot_input 26_colcon 27_formatted_labels_view 28_colcon_expand \
		29_recursive_all 30_expand_recursive_all 31_temp_dir 32_subgraph_edge \
		33_auto_color 34_diagrams_style || (echo "Failure!" && false)
	@${MAKE} TEST_NOT=! 04_node_cycle 05_style_cycle 19_style_notag_cycle \
		20_mixed_style_cycle 24_expand_validation || (echo "Failure!" && false)
	@${MAKE} 35_skill_install 36_list_styles || (echo "Failure!" && false)
	@echo "Success!"

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

spell:
	hunspell README.md

install_deps_apt:
	${APT_INSTALL} graphviz
	pipx install diagrams

install_deps_apt_focal:
	${APT_INSTALL} python3 python3-venv python3-pip

svg2png:
	find ${DIR} -iname "*.svg" | sed -e "s/\.svg$$//" | xargs -I {} sh -c "rsvg-convert {}.svg --format=png --output={}.png"

fmt:
	cp README.md README.md.back
	sed '/^Introduction$$/,$$!d' README.md.back > README.md
	pandoc --standalone --columns=80 --markdown-headings=setext --tab-stop=2 --to=gfm --toc --toc-depth=2 README.md -o README.fmt.md
	mv README.fmt.md README.md


.PHONY: test

# https://packaging.python.org/en/latest/tutorials/packaging-projects/
