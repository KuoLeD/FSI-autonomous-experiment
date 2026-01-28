Scripts for experiment control, automation, communication and video.

This repository contains the automated experimental control software developed for rigid circular cylinder fluid–structure interaction (FSI) experiments. The system integrates vibration control, towing control, synchronized video acquisition, and intelligent experimental point selection into a unified closed-loop framework.

The control architecture is built around Python-based main control programs that coordinate real-time experimental execution, hardware communication, and data acquisition. The vibration control module enables programmable forced oscillation and response regulation of the test cylinder, while the towing control module provides precise carriage motion control to achieve target inflow velocities and Reynolds numbers. A dedicated camera control module allows synchronized high-speed or continuous video recording during experiments.

In addition, this framework incorporates an intelligent sampling and optimization module based on Gaussian Process Regression (GPR) and Bayesian optimization. The optimization core is implemented in MATLAB and compiled into callable Python functions, enabling seamless integration into the Python control pipeline. This module autonomously selects new experimental parameter combinations to efficiently explore high-dimensional parameter spaces and improve experimental coverage and data efficiency.

Together, these components form a self-directed and automated experimental platform for fluid–structure interaction studies, enabling lights-out operation, reduced manual intervention, and reproducible data-driven experimental workflows. The software has been designed and validated for large-scale towing-tank experiments on rigid cylinders and can be adapted to other forced or free-vibration testing configurations.

This software was used to support automated data acquisition and experimental optimization in rigid-cylinder vortex-induced vibration studies. It is intended to facilitate reproducible experimental workflows and data-driven fluid–structure interaction research.
