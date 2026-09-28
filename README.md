# UFQ Server Infrastructure & Bot Service

Production deployment configurations, automated systemd process supervision, and deployment pipelines for asynchronous Telegram bot infrastructure running on Ubuntu Linux.

## System & Architecture Highlights
- **Process Supervision (systemd):** Self-healing background service configuration (ufq.service) ensuring automated recovery, failure isolation, and zero-downtime execution.
- **Automated Deployment Pipeline (deploy.sh):** Streamlined Bash deployment pipeline for pulling updates, managing virtual environments, and cycling daemon processes.
- **Security & Secret Isolation:** Complete isolation of sensitive tokens and database credentials via environment variables.

## Tech Stack
- **Host OS:** Ubuntu Linux LTS
- **Process Manager:** Linux systemd
- **Deployment Shell:** Bash
- **Application Runtime:** Python 3.10+, Asyncio

## License
MIT License
