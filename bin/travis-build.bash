#!/bin/bash
set -e
set -x # echo on

echo "This is travis-build.bash..."

echo "Installing the packages that CKAN requires..."
sudo apt-get update -qq
sudo apt-get install -y solr-jetty libcommons-fileupload-java

ver=$(python -c"import sys; print(sys.version_info.major)")
if [ $ver -eq 2 ]; then
    echo "python version 2"
elif [ $ver -eq 3 ]; then
    echo "python version 3"
else
    echo "Unknown python version: $ver"
fi

echo "Upgrading libmagic for ckanext-qa..."
# appears to upgrade it from 5.09-2 to 5.09-2ubuntu0.6 which seems to help the tests
sudo apt-get install libmagic1

echo "Installing CKAN and its Python dependencies..."
git clone https://github.com/ckan/ckan
pushd ckan

if [ -f requirement-setuptools.txt ]; then
    pip install -r requirement-setuptools.txt
fi

if [ $CKANVERSION == 'master' ]
then
    echo "CKAN version: master"
else
    CKAN_TAG=$(git tag | grep ^ckan-$CKANVERSION | sort --version-sort | tail -n 1)
    git checkout $CKAN_TAG
    echo "CKAN version: ${CKAN_TAG#ckan-}"
fi

if [ -f requirements-py2.txt ] && [ $ver -eq 2 ]
then
    pip install -r requirements-py2.txt
else
    pip install -r requirements.txt
fi
pip install -r dev-requirements.txt --allow-all-external
python setup.py develop

echo "Creating the PostgreSQL user and database..."
sudo -u postgres psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c 'CREATE DATABASE ckan_test WITH OWNER ckan_default;'

echo "Initialising the database..."
paster db init -c test-core.ini

popd

echo "Setting up Solr..."
# solr is multicore for tests on ckan master now, but it's easier to run tests
# on Travis single-core still.
# see https://github.com/ckan/ckan/issues/2972
sed -i -e 's/solr_url.*/solr_url = http:\/\/127.0.0.1:8983\/solr/' ckan/test-core.ini
printf "NO_START=0\nJETTY_HOST=127.0.0.1\nJETTY_PORT=8983\nJAVA_HOME=$JAVA_HOME" | sudo tee /etc/default/jetty
sudo cp ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml
sudo service jetty restart

echo "Installing dependency ckanext-report and its requirements..."
git clone --depth=50 https://github.com/datagovuk/ckanext-report.git
pushd ckanext-report
  if [ -f requirements-py2.txt ] && [ $ver -eq 2 ]; then
    pip install -r requirements-py2.txt
  elif [ -f requirements.txt ]; then
    pip install -r requirements.txt
  fi
  pip install --no-deps -e .
popd

echo "Installing dependency ckanext-archiver and its requirements..."
git clone --depth=50 https://github.com/ckan/ckanext-archiver.git
pushd ckanext-archiver
  if [ -f requirements-py2.txt ] && [ $ver -eq 2 ]; then
    pip install -r requirements-py2.txt
  elif [ -f requirements.txt ]; then
    pip install -r requirements.txt
  fi
  pip install --no-deps -e .
popd

echo "Installing ckanext-qa and its requirements..."
pip install -r requirements.txt
pip install -r dev-requirements.txt
python setup.py develop

echo "Moving test-core.ini into a subdir..."
mkdir -p subdir
cp test-core.ini subdir

echo "travis-build.bash is done."
