
# **Product Brief: Binocular**

## **1. Executive Summary**
Keeping high-value, offline devices up-to-date is a manual and error-prone chore. Binocular eliminates this hassle by automating firmware discovery. It is a self-hosted, responsive web application that maintains an inventory of your devices, uses extensible scripts to monitor manufacturer websites, and alerts you the moment a new update is available—ensuring your equipment always has the latest features and fixes.

## **2. Problem Statement**
The critical task of ensuring offline hardware runs the latest firmware is inefficient and fragmented. Users are forced to become manual librarians, repeatedly visiting disparate manufacturer support pages—a process that is **time-consuming**, **easy to forget**, and **prone to missing critical security patches or performance improvements**.

This manual process is:
*   **Inefficient:** Requires repetitive checking of multiple, distinct support websites.
*   **Error-prone:** It is easy to miss critical updates, bug fixes, or security patches.
*   **Fragmented:** Manufacturers use vastly different website layouts and versioning schemes for different product lines.

## **3. Target Audience**
**Primary User:** Homelab enthusiasts, professional photographers, and tech-savvy hobbyists who own and manage a portfolio of valuable, offline devices (e.g., 5-50+ items). For them, manual checking is a significant recurring time sink, and missing an update can mean lost functionality or compromised security.

**Environment:** Private, self-hosted local networks (Home Lab or small office LAN).

## **4. Core Functional Requirements**
Binocular's functionality is built around user-managed **Extension Modules**—compact scripts that know how to check for updates for a specific type of device. The core system provides the inventory, scheduler, and interface, while these modules provide the device-specific intelligence.

### **4.1. Device Inventory & Lifecycle Management**
*   **Inventory:** The system must allow the user to maintain a digital inventory of owned devices.
*   **Grouping:** Devices must be grouped by "Device Type" (e.g., "Sony E-Mount Lenses" vs. "Sony Alpha Bodies"), as firmware sources often differ by product line.
*   **Version Tracking:** For each device, the user must be able to record the currently installed firmware version.
*   **Update Workflow:** When a new version is detected and the user has physically updated their device, the web interface must provide a "one-click" confirmation action to update the stored local version to the new one, automatically resetting the alert status.
*   **Manual Checking:** From the main device inventory page, users must be able to manually trigger a firmware check:
    *   For an individual device.
    *   For all devices at once.
    *   The results must display in context, showing both the currently stored version and the latest found version side-by-side for clear, immediate comparison.

### **4.2. User-Managed Extension Modules**
*   **Pluggable Architecture:** Adding support for new **Device Types** must be done solely by creating or importing Extension Modules. The system must enforce a strict, well-documented contract that these scripts implement, guaranteeing they return data in a standardized format regardless of the target website's complexity.
*   **Module Lifecycle Management:** Users must have full control over modules via the web interface: uploading new ones, updating existing ones with improved logic, and deleting unused ones. *This design empowers users and fosters a potential community-shared library of modules.*

### **4.3. Automated Version Checking**
*   **Scheduling:** The system must periodically execute the extension scripts to scan for updates automatically.
*   **Granularity:** The user must be able to configure the automatic check frequency (e.g., daily, weekly) on a per-device-type basis.

### **4.4. Intelligence & Alerting**
*   **Version Comparison:** The system must compare the detected web version against the locally stored user version.
*   **Notification Dispatch:** If the web version is newer, the system must trigger a notification.
*   **Channels:** The system must support configurable notification channels. For the initial release, support is required for:
    *   **Email:** Must support standard SMTP configurations to work with common providers (e.g., Gmail).
    *   **Gotify**

### **4.5. System Logging & Visibility**
*   **Activity Log:** The system must maintain a log of all checking activity, both automated and manual (e.g., "Manual check started for Sony A7IV," "New version found," "Error parsing URL").
*   **UI Visibility:** This log must be viewable directly within the web interface for easy troubleshooting.
*   **Log Rotation:** To prevent storage bloat, the log must be a rolling file (limiting max size or line count) with automatic truncation of old entries.

### **4.6. Initial Device Support & Examples**
To deliver immediate value upon first launch and to serve as clear, working examples for users who wish to create their own modules, Binocular must ship with pre-installed, officially supported modules for two major platforms:
1.  **Sony Alpha System** (Cameras & Lenses)
    *   **Source:** `https://alphauniverse.com/firmware/`
2.  **Panasonic Lumix** (Micro Four Thirds Cameras & Lenses)
    *   **Source:** `https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html`

These modules will validate the core architecture and provide a template for user-created content.

## **5. Non-Functional Requirements (UX & Operations)**
*   **Responsive Interface:** The web application must be fully functional and optimized for mobile browsers (smartphones/tablets) as well as desktop browsers.
*   **Deployment Flexibility:**
    *   **Primary:** Distributable as a Docker container (hosted on a public registry) for simplicity.
    *   **Alternative:** Run directly on the host machine with standard language runtime prerequisites (e.g., Python/Node.js), catering to users who prefer not to use containers.
*   **Self-Contained Data Storage:** The application must not require an external database server (like Postgres or MySQL). All data persistence must be handled internally (e.g., embedded DB or flat files) to ensure a "batteries included" deployment.
*   **Lightweight & Practical Security:** The application is designed for a trusted, single-user environment on a private network. No user login needed.

## **6. Visual Design**

See [mockup.jsx](mockup.jsx) for how the website design should look like.