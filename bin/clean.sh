#!/bin/bash

echo "cleaning..."
rm -rf indexer/__pycache__
rm -rf search/__pycache__
rm -rf utils/__pycache__
rm -rf file_list.pkl
rm -rf index
rm -rf log
exit 0