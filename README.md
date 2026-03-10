# PM4PY Suite

**PM4PY Suite** is a modern desktop UI for **Process Mining with PM4PY**, built with **Flet**.  
It provides a comprehensive graphical interface for importing event logs, discovering process models, performing conformance checking, analyzing variants, and exporting results — all without writing code.

The application wraps many core **PM4PY** features into an easy-to-use UI designed for analysts, researchers, and students.

---

## Features

### Event Log Handling
- Import **XES**, **CSV**, and **Parquet** event logs
- CSV column mapping for case, activity, and timestamp
- Log statistics and overview

### Process Discovery
- **Alpha Miner** (Classic / Plus)
- **Inductive Miner** (IM / IMf / IMd)
- **Heuristics Miner**
- **Directly-Follows Graph (DFG)** discovery

### Conformance Checking
- **Token-based Replay**
- **Alignments-based Conformance Checking**
- Load external models (**PNML**, **BPMN**) or use discovered models

### Log Analysis
- Variant analysis (Top process variants)
- Event log statistics
- Performance analysis (waiting times)
- Social network analysis of resources

### Filtering
- Time range filtering
- Case size filtering
- Top-K variant filtering

### Simulation
- Simulate event logs from discovered Petri nets

### Export
- Export event logs:
  - XES
  - CSV
  - Parquet
- Export process models:
  - PNML
  - BPMN

---

## Technologies Used

- **Python**
- **Flet** – Modern Python UI framework
- **PM4PY** – Process mining library
- **Pandas** – Data processing
- **PyArrow** – Parquet support

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/pm4py-suite.git
cd pm4py-suite
````

### 2. Install Dependencies

```bash
pip install flet pm4py pandas pyarrow
```

---

## Run the Application

```bash
python app.py
```

Flet will start the UI and open the application in your browser or desktop window.

---

## Supported Event Log Formats

| Format      | Description                              |
| ----------- | ---------------------------------------- |
| **XES**     | Standard process mining event log format |
| **CSV**     | Custom event logs with column mapping    |
| **Parquet** | Efficient columnar data format           |

### Required Columns

| Column              | Meaning         |
| ------------------- | --------------- |
| `case:concept:name` | Case identifier |
| `concept:name`      | Activity name   |
| `time:timestamp`    | Event timestamp |

Optional:

| Column         | Purpose                              |
| -------------- | ------------------------------------ |
| `org:resource` | Required for Social Network Analysis |

---

## UI Modules

| Module           | Description                   |
| ---------------- | ----------------------------- |
| Log Import       | Load event logs               |
| Alpha Miner      | Classic discovery algorithm   |
| Inductive Miner  | Sound process discovery       |
| Heuristics Miner | Frequency-based discovery     |
| DFG Discovery    | Directly-Follows Graph        |
| Token Replay     | Basic conformance checking    |
| Alignments       | Optimal conformance checking  |
| Log Filtering    | Filter traces and events      |
| Variant Analysis | Top process variants          |
| Statistics       | Event log metrics             |
| Social Network   | Resource interaction analysis |
| Performance      | Waiting time analysis         |
| Simulation       | Generate synthetic event logs |
| Export           | Save logs and models          |

---

## Example Workflow

1. Import an **event log**
2. Run **Inductive Miner**
3. Inspect the **Petri net**
4. Run **Token Replay**
5. Analyze **Variants**
6. Export the resulting **BPMN or PNML model**

---

## Requirements

* Python **3.9+**
* PM4PY compatible environment

Tested with:

* Python 3.10
* PM4PY latest version
* Flet 0.82+

---

## Known Limitations

* Alignments may take several minutes on large logs
* Social network analysis requires `org:resource`
* Very large logs (>1M events) may require more memory

---

## License

MIT License

---

## Acknowledgements

* **PM4PY Team**
  [https://pm4py.fit.fraunhofer.de/](https://pm4py.fit.fraunhofer.de/)

* **Flet Framework**
  [https://flet.dev/](https://flet.dev/)

---

## Contributing

Pull requests and improvements are welcome.

Possible improvements:

* OCEL support
* Additional discovery algorithms
* Interactive process visualization
* Dashboard charts
* Docker deployment

---

## Author

Process Mining UI built on top of **PM4PY** using **Flet**.
