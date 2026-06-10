# SDD Project Configuration

<!-- Managed by SDD bootstrap workflows. Keep headings and bold keys unchanged. -->

## Product Document

**Path**: specs/prd.md

## Technical Context Document

**Path**: specs/sad.md

## Deployment & Operations Document

**Path**: specs/dod.md

## Project Plan

<!-- A high-level decomposition of the project into epics with dependency ordering and execution waves. -->
<!-- Registered by /sddp-projectplan when specs/project-plan.md is created. -->

**Path**: specs/project-plan.md

## Checklist Settings

**MaxChecklistCount**: 3

## Autopilot

**Enabled**: true

## Loop Settings

**MaxIterations**: 10

## QC Strictness

<!-- Profile: standard | strict | minimal. Override Categories: comma-separated category:required|optional pairs. -->

**Profile**: standard
**Override Categories**:

## Derived QC Policy

<!-- Managed by /sddp-init. QC reads this section — do not edit manually. -->

**Coverage Target**: 80
**Required Categories**: linting, static analysis, security, coverage
