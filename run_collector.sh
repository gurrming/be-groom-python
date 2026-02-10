#!/bin/bash
cd /Users/anseungju/Desktop/dev_practice
source venv/bin/activate
python3 src/collectors/community_aggregator.py >> collector.log 2>&1
