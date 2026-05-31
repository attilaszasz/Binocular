# Extension Boundary

This package is the future integration point for user-managed extension modules.

Extension modules are not sandboxed. They will run in-process with the same application privileges as the core backend, so operators must vet any module before installing it. The container runs as a non-root user to reduce host-level blast radius, but that is not a sandbox and must not be described as one.