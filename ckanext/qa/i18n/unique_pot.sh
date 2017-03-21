#!/bin/bash

# When you copy templates from CKAN (or other plugins) you end up with already translated translations in your pot file.
# This script filters them out from your .pot file. Run it right after `python setup.py extract_messages`

PLUGIN_NAME=qa
PLUGIN_DEPENDENCIES="report archiver"

SAVE_REUSED=0
VERBOSE=0
CURR_DIR=$(readlink -m $0/..)
SRC_DIR=$(readlink -m $0/../../../../..)

while getopts ":p:r:" opt; do
  case $opt in
    l) LANGUAGES="$OPTARG"
    ;;
    p) PLUGIN_DEPENDENCIES="$OPTARG"
    ;;
    r) SAVE_REUSED=1
    ;;
    v) VERBOSE=1
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
    ;;
  esac
done

function run_verbose {
 if [ $VERBOSE ]; then
  echo "# Running: $1"
 fi
 eval $1
}

# Find strings that we have reused from core CKAN and other plugins
DEP_POTS=""
for PLUGIN in $PLUGIN_DEPENDENCIES; do
  DEP=$SRC_DIR/ckanext-$PLUGIN/ckanext/$PLUGIN/i18n/ckanext-$PLUGIN.pot
  echo $DEP
  if [ -f $DEP ]; then
    DEP_POTS="$DEP_POTS $DEP"
  else
    echo "Warning: .pot file for dependent $PLUGIN plugin doesn't exist, skipping $DEP"
  fi
done
echo $DEP_POTS

run_verbose "msgcat $SRC_DIR/ckan/ckan/i18n/ckan.pot $DEP_POTS -o $CURR_DIR/_dependencies.pot"

# Identify reused translations
touch $CURR_DIR/_reused_translations.pot
run_verbose "msgcat --use-first --more-than=1 $CURR_DIR/_dependencies.pot $CURR_DIR/ckanext-$PLUGIN_NAME.pot -o $CURR_DIR/_reused_translations.pot"

# Leave only unique strings in our pot
run_verbose "msgcat --unique $CURR_DIR/ckanext-$PLUGIN_NAME.pot $CURR_DIR/_reused_translations.pot -o $CURR_DIR/ckanext-$PLUGIN_NAME.pot"

rm $CURR_DIR/_dependencies.pot
if [ ! $SAVE_REUSED ]; then
  rm $CURR_DIR/_reused_translations.pot
else
  echo "Saving $CURR_DIR/_reused_translations.pot"
fi

echo ""
echo "I've updated $CURR_DIR/ckanext-$PLUGIN_NAME.pot."