# Blackboard CLI

> A terminal tool for browsing and downloading course files from [SUSTech Blackboard](https://bb.sustech.edu.cn/).

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-0078D6?logo=windows&logoColor=white) ![License](https://img.shields.io/badge/License-MIT-green)

------


## 📦 Installation
**1. Clone the repository:**

```bash
git clone https://github.com/linwenqi1/blackboard-cli
cd blackboard-cli
```
**2. Install dependencies:**

```bash
pip install -r requirements.txt
```

**3. Browser Setup (If not already installed):**

The tool automatically uses your existing Chrome or Microsoft Edge. If neither is available, install the built-in browser:

```bash
python -m playwright install chromium
```
> **Linux users:** If the above command fails with missing library errors, ask your administrator to run:
> ```bash
> sudo python3 -m playwright install-deps chromium
> ```

## 🚀 Usage

```bash
python blackboard-cli.py
```

Enter your SUSTech credentials and a download directory when prompted.

## 📋 Commands

| Command       | Description                       |
| ------------- | --------------------------------- |
| `ls`          | List items at current level       |
| `cd [ID]`     | Enter a course or module          |
| `cd ..`       | Go back                           |
| `get [ID...]` | Download file(s) by ID            |
| `get all`     | Download everything at this level |
| `exit` / `q`  | Quit                              |

## 📁 File Organization

| Level        | Save Path                            |
| ------------ | ------------------------------------ |
| Course level | `DownloadDir/CourseName/ModuleName/` |
| Module level | `DownloadDir/`                       |
