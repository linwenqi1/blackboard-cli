# Blackboard CLI

> A terminal tool for browsing and downloading course files from [SUSTech Blackboard](https://bb.sustech.edu.cn/).

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white) ![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white) ![License](https://img.shields.io/badge/License-MIT-green)

------

## 📦 Installation

```bash
pip install -r requirements.txt
```

> Chrome or Microsoft Edge is recommended over bundled Chromium.

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
