# Changelog

All notable changes to this project will be documented in this file. See [commit-and-tag-version](https://github.com/absolute-version/commit-and-tag-version) for commit guidelines.

## [1.3.0](///compare/v1.2.2...v1.3.0) (2025-06-12)


### ⚠ BREAKING CHANGES

* refactor app for better concern separation

* refactor app for better concern separation f7bed20

## [1.2.2](///compare/v1.2.1...v1.2.2) (2025-06-10)

## [1.2.1](///compare/v1.2.0...v1.2.1) (2025-06-10)


### ⚠ BREAKING CHANGES

* add live log streaming to the UI
* reduce hard penality of overlapping tasks

### Features

* add configurable employee count and schedule days ba9a984
* add live log streaming to the UI f77d330
* add mock project loading functionality 200196d
* add mock projects to config 4634124
* add scaling of employee availability generation fc20e9b
* improve solver status and constraint analysis 77b90d2


### Bug Fixes

* improve UI and schedule data handling, restore global state object 8aa0c1d
* reduce hard penality of overlapping tasks 32df40d

## [1.2.0](///compare/v1.1.0...v1.2.0) (2025-06-10)


### ⚠ BREAKING CHANGES

* add task to skill matching

### Features

* add task to skill matching 76af8db

## [1.1.0](///compare/v1.0.1...v1.1.0) (2025-06-10)


### Features

* add multiple input projects dd21d63
* add task dependency constraint 927121b


### Bug Fixes

* fix task sorting per start date d41ca29

## [1.0.2](///compare/v1.0.1...v1.0.2) (2025-06-09)

## [1.0.1](///compare/v1.0.0...v1.0.1) (2025-06-09)

## 1.0.0 (2025-06-09)


### ⚠ BREAKING CHANGES

* add basic gradio app and constraint solver

### Features

* add basic gradio app and constraint solver 6e6c448
* add Markdown analyzer utility a364fcc
* add task composer agent 2153f15
* **deploy:** setup initial Docker environment c6e1cef
* integrated timetable solver with task_composer_agent 391ae1e
* refactor app for improved data generation and polling b836318


### Bug Fixes

* fix import path for agent utils 5c01b67
