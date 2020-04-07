#!/bin/bash
cd COVID-19
git pull
cd ..
venv/scripts/python.exe graphing.py -v
venv/scripts/python.exe graphing.py -v -d -s 0
/c/Program\ Files\ \(x86\)/Google/Chrome/Application/chrome.exe images/UK-cases-shifted-14-days.png
/c/Program\ Files\ \(x86\)/Google/Chrome/Application/chrome.exe images/UK-deltas-unshifted.png
